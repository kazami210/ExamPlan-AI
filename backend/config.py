import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

def load_env():
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and v:
                        os.environ[k] = v

load_env()

DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

raw_db_url = os.getenv("DATABASE_URL", "").strip()
if raw_db_url:
    # SQLAlchemy requires postgresql:// instead of legacy postgres://
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
    DATABASE_URL = raw_db_url
else:
    DATABASE_URL = f"sqlite:///{DATA_DIR / 'exam_plan.db'}"

def get_google_client_id() -> str:
    load_env()
    # Support direct variable or common frontend build prefixes
    candidates = [
        "GOOGLE_CLIENT_ID",
        "VITE_GOOGLE_CLIENT_ID",
        "NEXT_PUBLIC_GOOGLE_CLIENT_ID",
        "REACT_APP_GOOGLE_CLIENT_ID",
    ]
    for key in candidates:
        val = os.getenv(key, "").strip()
        if val:
            return val
    return ""

GOOGLE_CLIENT_ID = get_google_client_id()

# AI Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()

def has_gemini_key() -> bool:
    return bool(GEMINI_API_KEY and len(GEMINI_API_KEY) > 10)
