"""Pool of API keys with per-key rate limiting and upload cooldowns.

The hackathon hands out several keys per team. Each key carries its own
per-minute budget and its own five-minute upload cooldown, so rotating over a
pool multiplies both.
"""

import os
import re
import threading
import time
from collections import deque
from pathlib import Path

from ..config import (
    ENV_FILE,
    RATE_LIMITS,
    RATE_WINDOW_S,
    UNLIMITED_PATHS,
    UPLOAD_COOLDOWN_S,
    UPLOAD_PATH,
)

KEY_PATTERN = re.compile(r"hyppe_[A-Za-z0-9_\-]+")


class NoKeysError(RuntimeError):
    pass


def load_keys(env_file: Path = ENV_FILE) -> list[str]:
    """Read keys from HYPPE_KEYS, otherwise scrape every token from the env file.

    The env file is a bare list of keys rather than KEY=VALUE pairs, so both
    shapes are accepted.
    """
    text = os.environ.get("HYPPE_KEYS") or ""
    if not text and env_file.exists():
        text = env_file.read_text(encoding="utf-8")
    keys = list(dict.fromkeys(KEY_PATTERN.findall(text)))
    if not keys:
        raise NoKeysError(
            f"no hyppe_ keys found in HYPPE_KEYS or {env_file}"
        )
    return keys


def bucket_for(path: str) -> str | None:
    """Rate-limit bucket of an endpoint, or None when it is unmetered."""
    if path in UNLIMITED_PATHS:
        return None
    return path if path in RATE_LIMITS else "other"


class ApiKey:
    def __init__(self, value: str):
        self.value = value
        self.hits: dict[str, deque[float]] = {}
        self.next_upload_at = 0.0
        self.blocked_until = 0.0

    @property
    def label(self) -> str:
        return f"{self.value[:11]}..{self.value[-4:]}"

    def __repr__(self) -> str:
        return f"ApiKey({self.label})"

    def _window(self, bucket: str) -> deque[float]:
        return self.hits.setdefault(bucket, deque())

    def free_at(self, bucket: str | None, now: float) -> float:
        """Timestamp at which this key may serve the bucket again."""
        ready = self.blocked_until
        if bucket is not None:
            window = self._window(bucket)
            while window and now - window[0] >= RATE_WINDOW_S:
                window.popleft()
            if len(window) >= RATE_LIMITS[bucket]:
                ready = max(ready, window[0] + RATE_WINDOW_S)
        return ready

    def record(self, bucket: str | None, now: float) -> None:
        if bucket is not None:
            self._window(bucket).append(now)


class KeyPool:
    def __init__(self, keys: list[str] | None = None):
        values = list(dict.fromkeys(keys)) if keys else load_keys()
        if not values:
            raise NoKeysError("empty key pool")
        self.keys = [ApiKey(v) for v in values]
        self._lock = threading.Lock()
        self._cursor = 0

    @classmethod
    def from_env(cls, env_file: Path = ENV_FILE) -> "KeyPool":
        return cls(load_keys(env_file))

    def __len__(self) -> int:
        return len(self.keys)

    def acquire(self, path: str, timeout: float | None = None) -> ApiKey:
        """Round-robin the next key allowed to call `path`, waiting if needed.

        Waiting is the point: it keeps parallel judge calls under the per-minute
        cap instead of collecting 429s.
        """
        bucket = bucket_for(path)
        is_upload = path == UPLOAD_PATH
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            with self._lock:
                now = time.monotonic()
                soonest = None
                for offset in range(len(self.keys)):
                    index = (self._cursor + offset) % len(self.keys)
                    key = self.keys[index]
                    ready = key.free_at(bucket, now)
                    if is_upload:
                        ready = max(ready, key.next_upload_at)
                    if ready <= now:
                        key.record(bucket, now)
                        self._cursor = (index + 1) % len(self.keys)
                        return key
                    soonest = ready if soonest is None else min(soonest, ready)
            wait = max(0.01, min((soonest or now) - now, 0.25))
            if deadline is not None and time.monotonic() + wait > deadline:
                raise TimeoutError(f"no key available for {path} within {timeout}s")
            time.sleep(wait)

    def mark_upload(self, key: ApiKey, seconds: float | None = None) -> None:
        with self._lock:
            cooldown = UPLOAD_COOLDOWN_S if seconds is None else seconds
            key.next_upload_at = max(key.next_upload_at, time.monotonic() + cooldown)

    def penalize(self, key: ApiKey, seconds: float) -> None:
        """Park a key after a 429 so retries land on a different one."""
        with self._lock:
            key.blocked_until = max(key.blocked_until, time.monotonic() + seconds)

    def upload_ready_in(self) -> float:
        """Seconds until any key may upload again."""
        with self._lock:
            now = time.monotonic()
            return min(max(0.0, k.next_upload_at - now) for k in self.keys)

    def status(self) -> list[dict[str, object]]:
        with self._lock:
            now = time.monotonic()
            return [
                {
                    "key": k.label,
                    "upload_in_s": round(max(0.0, k.next_upload_at - now), 1),
                    "blocked_in_s": round(max(0.0, k.blocked_until - now), 1),
                    "used_last_minute": {
                        bucket: len(window) for bucket, window in k.hits.items() if window
                    },
                }
                for k in self.keys
            ]
