"""HTTP client for the hyppe API: retries, backoff and key rotation."""

import json
import time
import urllib.error
import urllib.request
from typing import Any

from ..config import (
    API_URL,
    BACKOFF_BASE_S,
    BACKOFF_CAP_S,
    REQUEST_ATTEMPTS,
    REQUEST_TIMEOUT_S,
    UPLOAD_PATH,
    USER_AGENT,
)
from .keys import ApiKey, KeyPool


class ApiError(RuntimeError):
    def __init__(self, path: str, status: int, payload: Any):
        self.path = path
        self.status = status
        self.payload = payload
        super().__init__(f"{path} -> HTTP {status}: {payload!r}")


def _retry_after(exc: urllib.error.HTTPError) -> float | None:
    raw = exc.headers.get("Retry-After") if exc.headers else None
    try:
        value = float(raw) if raw else 0.0
    except ValueError:
        return None
    return value or None


class HyppeClient:
    def __init__(
        self,
        pool: KeyPool | None = None,
        url: str = API_URL,
        timeout: float = REQUEST_TIMEOUT_S,
        attempts: int = REQUEST_ATTEMPTS,
    ):
        self.pool = pool if pool is not None else KeyPool.from_env()
        self.url = url.rstrip("/")
        self.timeout = timeout
        self.attempts = attempts

    def request(
        self, path: str, data: dict | None = None, *, key: ApiKey | None = None
    ) -> tuple[int, Any]:
        """(status, payload). A non-None `data` makes it a JSON POST.

        Status 0 means the request never reached the server. 503 and 429 are
        retried on a fresh key, except 429 on the upload endpoint, which is a
        real cooldown rather than congestion.
        """
        result: tuple[int, Any] = (0, "no attempt made")
        for attempt in range(self.attempts):
            used = key if key is not None else self.pool.acquire(path)
            request = urllib.request.Request(self.url + path)
            request.add_header("X-API-Key", used.value)
            request.add_header("User-Agent", USER_AGENT)
            if data is not None:
                request.add_header("Content-Type", "application/json")
                request.data = json.dumps(data).encode()
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    status = response.status
                    payload = json.loads(response.read().decode())
                if path == UPLOAD_PATH:
                    self.pool.mark_upload(used)
                return status, payload
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", "replace")
                pause = _retry_after(exc)
                if exc.code == 429:
                    if path == UPLOAD_PATH:
                        self.pool.mark_upload(used, seconds=pause)
                    else:
                        self.pool.penalize(used, pause or 30.0)
                result = (exc.code, body)
                retryable = exc.code == 503 or (exc.code == 429 and path != UPLOAD_PATH)
                if not retryable or attempt == self.attempts - 1:
                    return result
                self._sleep(pause, attempt)
            except urllib.error.URLError as exc:
                result = (0, f"network: {exc}")
                if attempt == self.attempts - 1:
                    return result
                self._sleep(None, attempt)
        return result

    def call(self, path: str, data: dict | None = None, *, key: ApiKey | None = None) -> Any:
        """Same as `request` but raises `ApiError` on anything but 200."""
        status, payload = self.request(path, data, key=key)
        if status != 200:
            raise ApiError(path, status, payload)
        return payload

    def _sleep(self, pause: float | None, attempt: int) -> None:
        time.sleep(min(pause or BACKOFF_BASE_S * 2**attempt, BACKOFF_CAP_S))
