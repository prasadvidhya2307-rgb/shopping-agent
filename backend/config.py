"""Central configuration and environment handling.

Security rule: this module never logs or returns secret values. Callers can
ask *whether* a key is configured, but the key itself is only read when a
Groq client is actually constructed (see ``llm.py``).
"""

from pathlib import Path

from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

# Database ------------------------------------------------------------------
DB_PATH = BASE_DIR / "store.db"
RESOURCES_DIR = BASE_DIR / "assets"

# Groq models ----------------------------------------------------------------
# Override with GROQ_MODEL / GROQ_VISION_MODEL if your Groq account has access
# to different models. The reasoning default is a tool-calling model widely
# available on current Groq accounts; availability varies by account/region.
REASONING_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
VISION_MODEL = os.getenv(
    "GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"
)

# Image upload policy --------------------------------------------------------
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_IMAGE_EDGE = 2048
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp"}

# Behaviour ------------------------------------------------------------------
DEFAULT_SESSION_ID = "local-session"
CONFIRMATION_TTL_SECONDS = 600  # 10 minutes
MAX_RECOMMENDATIONS = 8

# Never display these in errors sent to the UI.
_SENSITIVE_ENV_NAMES = ("GROQ_API_KEY", "OPENAI_API_KEY", "API_KEY", "TOKEN", "SECRET")


def groq_api_key() -> str | None:
    """Return the API key for internal client construction only."""
    value = os.getenv("GROQ_API_KEY")
    return value.strip() if value and value.strip() else None


def has_groq_credentials() -> bool:
    return groq_api_key() is not None


def redact(text: str) -> str:
    """Remove anything that resembles a secret from log/error text."""
    result = str(text)
    key = groq_api_key()
    if key:
        result = result.replace(key, "[REDACTED]")
    for name in _SENSITIVE_ENV_NAMES:
        result = result.replace(f"{name}=", "[REDACTED]=")
    return result
