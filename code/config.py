"""
Configuration loading and environment-variable helpers for Message Notification Router.
Architecture-neutral configuration management without external dependencies.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv, find_dotenv
    # First try to find it in the current directory or parent directories
    dotenv_path = find_dotenv(usecwd=True)
    if not dotenv_path:
        # Fallback to specifically checking the parent directory
        parent_env = Path(__file__).resolve().parent.parent.parent / ".env"
        if parent_env.exists():
            dotenv_path = str(parent_env)
    
    if dotenv_path:
        load_dotenv(dotenv_path=dotenv_path)
except ImportError:
    pass

# Resolve absolute paths relative to repository root
REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = REPO_ROOT / "dataset"
CODE_DIR = REPO_ROOT / "code"
TESTS_DIR = REPO_ROOT / "tests"
ENV_EXAMPLE_PATH = REPO_ROOT / ".env.example"
OUTPUT_DIR = REPO_ROOT / "outputs"
CACHE_DIR = REPO_ROOT / ".cache"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# Provider Configuration
LLM_PROVIDER = os.environ.get("MODEL_PROVIDER", "gemini")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
LLM_MODEL_ID = os.environ.get("MODEL_NAME", "auto")

IMAGE_PROVIDER = os.environ.get("IMAGE_PROVIDER", "gemini")
IMAGE_MODEL_NAME = os.environ.get("IMAGE_MODEL_NAME", "auto")

ASR_PROVIDER = os.environ.get("ASR_PROVIDER", "gemini")
ASR_MODEL_NAME = os.environ.get("ASR_MODEL_NAME", "auto")

TEXT_FALLBACK_PROVIDER = os.environ.get("TEXT_FALLBACK_PROVIDER", "groq")
ASR_FALLBACK_PROVIDER = os.environ.get("ASR_FALLBACK_PROVIDER", "groq")

# Fallback Configuration
# Fallback Configuration
FORCE_DETERMINISTIC_FALLBACK = os.environ.get("FORCE_DETERMINISTIC_FALLBACK", "false").lower() == "true"
if not GEMINI_API_KEY:
    FORCE_DETERMINISTIC_FALLBACK = True

# Limits and Budgets
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "1"))
MAX_CALLS_PER_MESSAGE = int(os.environ.get("MAX_CALLS_PER_MESSAGE", "2"))
TIMEOUT_SECONDS = int(os.environ.get("TIMEOUT_SECONDS", "30"))

# Rate-limit safe execution
# Free tier typically: 15 RPM for gemini-2.0-flash-lite, 10 RPM for gemini-2.0-flash
# Set to conservative default to avoid systematic quota exhaustion
MAX_REQUESTS_PER_MINUTE = int(os.environ.get("MAX_REQUESTS_PER_MINUTE", "10"))
MIN_SECONDS_BETWEEN_CALLS = float(os.environ.get("MIN_SECONDS_BETWEEN_CALLS", "7.0"))

# Verified working model IDs (as of 2026-08-02):
# gemini-2.0-flash-lite, gemini-2.0-flash, gemini-2.5-flash
# gemini-3.5-flash is verified as working and not rate limited
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"



def get_env_var(key: str, default: str | None = None) -> str | None:
    """Retrieve an environment variable cleanly."""
    return os.environ.get(key, default)


def resolve_dataset_path(filename: str) -> Path:
    """Resolve an absolute path for a dataset file."""
    return DATASET_DIR / filename


def is_placeholder_value(val: str) -> bool:
    """Check if a string looks like a placeholder rather than a real secret."""
    lower_val = val.lower()
    if lower_val in ("info", "debug", "warning", "error", "true", "false", "0", "1", "gemini", "groq", "auto"):
        return True
    return any(
        token in lower_val
        for token in ("replace", "placeholder", "your_", "here", "example")
    )


def validate_env_example_placeholders(path: Path | None = None) -> bool:
    """
    Verify that .env.example exists and contains only placeholder values.
    Returns True if valid, raises ValueError if a suspected real secret is found.
    """
    target = path or ENV_EXAMPLE_PATH
    if not target.exists():
        raise FileNotFoundError(f"Missing expected file: {target}")

    with open(target, mode="r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                value = value.strip()
                if value and not is_placeholder_value(value):
                    raise ValueError(
                        f"Suspected non-placeholder secret in {target} at line {line_num} ({key})"
                    )
    return True
