"""Central configuration: paths, API coordinates and task constants."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("PS_DATA_DIR") or ROOT / "data")
RUNS_DIR = Path(os.environ.get("PS_RUNS_DIR") or ROOT / "runs")
ENV_FILE = Path(os.environ.get("PS_ENV_FILE") or ROOT / ".env")
PROMOTERS_CSV = Path(os.environ.get("PS_PROMOTERS_CSV") or DATA_DIR / "Promotory.csv")
PROMOTERS_CSV_DELIMITER = ";"

API_URL = (os.environ.get("PS_API_URL") or "https://hyppe.futura.foundation").rstrip("/")

# Requests go through urllib; Cloudflare answers "error code: 1010" without a browser UA.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)
REQUEST_TIMEOUT_S = 900.0
REQUEST_ATTEMPTS = 6
BACKOFF_BASE_S = 0.4
BACKOFF_CAP_S = 8.0

SEQ_LENGTH = 800
ALPHABET = frozenset("ACGTN")
MAX_N_FRACTION = 0.10
MAX_N_COUNT = int(SEQ_LENGTH * MAX_N_FRACTION)
SUBMISSION_LIMIT = 100
MAX_FASTA_CHARS = 2_000_000

UPLOAD_PATH = "/wgraj"
UPLOAD_COOLDOWN_S = 300.0

# Per key, per minute. Endpoints not listed here share the "other" budget.
RATE_LIMITS = {
    "/sedzia": 600,
    "/nawigator/mapa": 600,
    "/nawigator/edycje": 600,
    "other": 240,
}
UNLIMITED_PATHS = frozenset({"/me", "/ranking", "/dziki"})
RATE_WINDOW_S = 60.0
