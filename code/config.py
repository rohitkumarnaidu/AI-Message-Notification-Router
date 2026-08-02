"""
Configuration loading and environment-variable helpers for Message Notification Router.
Architecture-neutral configuration management without external dependencies.
"""

import os
from pathlib import Path

# Resolve absolute paths relative to repository root
REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = REPO_ROOT / "dataset"
CODE_DIR = REPO_ROOT / "code"
TESTS_DIR = REPO_ROOT / "tests"
ENV_EXAMPLE_PATH = REPO_ROOT / ".env.example"


def get_env_var(key: str, default: str | None = None) -> str | None:
    """Retrieve an environment variable cleanly."""
    return os.environ.get(key, default)


def resolve_dataset_path(filename: str) -> Path:
    """Resolve an absolute path for a dataset file."""
    return DATASET_DIR / filename


def is_placeholder_value(val: str) -> bool:
    """Check if a string looks like a placeholder rather than a real secret."""
    lower_val = val.lower()
    if lower_val in ("info", "debug", "warning", "error", "true", "false", "0", "1"):
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
