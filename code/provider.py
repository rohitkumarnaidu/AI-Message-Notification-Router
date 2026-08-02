"""
Phase 7 Provider — rate-limit-safe, resumable, deterministic-fallback hybrid.

Design:
- Uses verified model identifier (gemini-2.0-flash-lite confirmed 2026-08-02)
- Enforces minimum inter-call delay to stay within free-tier quota
- Catches 429 and immediately raises ProviderFallbackError (no sleep loops)
- Bounded schema repair: max 2 attempts
- Per-message result cache keyed by message_id + model + prompt_version
- All API errors fall through to deterministic fallback — never crash the pipeline
"""
import json
import time
import hashlib
from pathlib import Path
from schemas import RouterDecision
from config import (
    FORCE_DETERMINISTIC_FALLBACK,
    LLM_PROVIDER,
    LLM_MODEL_ID,
    GEMINI_API_KEY,
    GROQ_API_KEY,
    DEFAULT_GEMINI_MODEL,
    MIN_SECONDS_BETWEEN_CALLS,
    CACHE_DIR,
)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ProviderFallbackError(Exception):
    """Raised when the API is unavailable, rate-limited, or keys are missing."""
    pass


class SchemaValidationError(Exception):
    """Raised when the LLM output violates the required JSON schema."""
    pass


# ---------------------------------------------------------------------------
# Result cache (per message, keyed by content hash)
# ---------------------------------------------------------------------------

_DECISION_CACHE_FILE = Path(CACHE_DIR) / "decision_cache.json"
_PROMPT_VERSION = "p7v1"  # bump when prompt logic changes


def _load_decision_cache() -> dict:
    if _DECISION_CACHE_FILE.exists():
        try:
            with open(_DECISION_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_decision_cache(cache: dict) -> None:
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    with open(_DECISION_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def _cache_key(message_id: str, model: str, prompt: str) -> str:
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    return f"{_PROMPT_VERSION}|{message_id}|{model}|{prompt_hash}"


# ---------------------------------------------------------------------------
# Inter-call pacing
# ---------------------------------------------------------------------------

_last_call_time: float = 0.0


def _pace() -> None:
    """Block until MIN_SECONDS_BETWEEN_CALLS has elapsed since the last call."""
    global _last_call_time
    elapsed = time.monotonic() - _last_call_time
    wait = MIN_SECONDS_BETWEEN_CALLS - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_call_time = time.monotonic()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

ALLOWED_ACTIONS = {"notify", "digest", "mute"}
ALLOWED_TYPES = {
    "personal", "urgent", "event", "payment", "business_update",
    "promotion", "greeting", "forward", "spam", "scam", "unknown",
}


def _validate_parsed(parsed: dict) -> RouterDecision:
    """Validate parsed LLM JSON and return a RouterDecision or raise SchemaValidationError."""
    action = parsed.get("action")
    if action not in ALLOWED_ACTIONS:
        raise SchemaValidationError(f"Invalid action: {action!r} (allowed: {ALLOWED_ACTIONS})")

    msg_type = parsed.get("message_type", "unknown")
    if msg_type not in ALLOWED_TYPES:
        parsed["message_type"] = "unknown"

    conf = parsed.get("confidence", 0.7)
    try:
        conf = float(conf)
    except (TypeError, ValueError):
        raise SchemaValidationError(f"Non-numeric confidence: {conf!r}")
    if not (0.0 <= conf <= 1.0):
        raise SchemaValidationError(f"Confidence out of range: {conf}")

    # evidence_message_ids may be missing or a list
    ev = parsed.get("evidence_message_ids", [])
    if not isinstance(ev, list):
        parsed["evidence_message_ids"] = []

    return RouterDecision(**parsed)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_structured_decision(
    prompt: str, message_id: str = "unknown"
) -> RouterDecision:
    """
    Call the configured LLM API with rate-limit safety.

    Raises ProviderFallbackError on any failure so the caller can fall back
    cleanly to the deterministic policy.

    Never sleeps in a long retry loop — 429 triggers immediate fallback.
    """
    if FORCE_DETERMINISTIC_FALLBACK:
        raise ProviderFallbackError("Deterministic fallback forced (no API key or env flag).")

    model_name = DEFAULT_GEMINI_MODEL if LLM_MODEL_ID == "auto" else LLM_MODEL_ID

    # Check decision cache first
    cache = _load_decision_cache()
    key = _cache_key(message_id, model_name, prompt)
    if key in cache:
        try:
            return RouterDecision(**cache[key])
        except Exception:
            del cache[key]

    try:
        if LLM_PROVIDER == "gemini":
            from google import genai
            from google.genai import types
            from google.genai.errors import APIError

            client = genai.Client(api_key=GEMINI_API_KEY)

            # Enforce inter-call pacing BEFORE making the request
            _pace()

            # Bounded schema-repair loop: max 2 attempts
            for attempt in range(2):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.0,
                        ),
                    )
                except APIError as api_err:
                    if api_err.code == 429:
                        raise ProviderFallbackError(
                            f"Rate limit (429) on {model_name} — falling back to deterministic."
                        )
                    raise ProviderFallbackError(
                        f"Gemini API error {api_err.code}: {str(api_err)[:120]}"
                    )

                try:
                    raw_json = response.text
                    parsed = json.loads(raw_json)
                    decision = _validate_parsed(parsed)

                    # Cache successful result
                    cache[key] = {
                        "action": decision.action,
                        "message_type": decision.message_type,
                        "reason": decision.reason,
                        "confidence": decision.confidence,
                        "evidence_message_ids": decision.evidence_message_ids,
                    }
                    _save_decision_cache(cache)
                    return decision

                except (json.JSONDecodeError, SchemaValidationError, TypeError, KeyError) as parse_err:
                    if attempt == 1:
                        raise ProviderFallbackError(
                            f"Schema validation failed after 2 attempts: {parse_err}"
                        )
                    # Add repair instruction and retry once
                    prompt = (
                        prompt
                        + f"\n\nPREVIOUS OUTPUT ERROR: {parse_err}. "
                        "Return ONLY valid JSON with keys: action, message_type, reason, confidence, evidence_message_ids."
                    )
                    _pace()

        else:
            raise ProviderFallbackError(f"Unsupported provider: {LLM_PROVIDER!r}")

    except ProviderFallbackError:
        raise
    except Exception as exc:
        raise ProviderFallbackError(f"Unexpected SDK error: {exc}") from exc
