"""
Media Processor - Rate limit safe, resumable, caching processor for images and audio.
"""
import os
import json
import hashlib
import time
from pathlib import Path
from schemas import MediaAnalysis
from config import (
    CACHE_DIR,
    LLM_PROVIDER,
    LLM_MODEL_ID,
    GEMINI_API_KEY,
    IMAGE_MODEL_NAME,
    ASR_MODEL_NAME,
    DEFAULT_GEMINI_MODEL,
    MIN_SECONDS_BETWEEN_CALLS
)

_CACHE_FILE = Path(CACHE_DIR) / "media_cache.json"
_PROMPT_VERSION = "p7v2"  # bump when prompt logic changes

# Inter-call pacing shared state
_last_call_time: float = 0.0

def _pace() -> None:
    """Block until MIN_SECONDS_BETWEEN_CALLS has elapsed since the last call."""
    global _last_call_time
    elapsed = time.monotonic() - _last_call_time
    wait = MIN_SECONDS_BETWEEN_CALLS - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_call_time = time.monotonic()

def _load_cache() -> dict:
    if _CACHE_FILE.exists():
        try:
            with open(_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def _save_cache(cache: dict):
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    with open(_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2)

def _hash_file(filepath: Path) -> str:
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def process_media(media_id: str, media_type: str, filepath: str) -> MediaAnalysis:
    """Process an image or voice note, returning a structured MediaAnalysis."""
    repo_root = Path(__file__).resolve().parent.parent
    full_path = repo_root / filepath
    
    if not full_path.exists():
        return MediaAnalysis(
            media_id=media_id,
            media_type=media_type,
            extracted_text="",
            summary="",
            language="",
            urgency_signals=[],
            risk_signals=[],
            promotion_signals=[],
            event_signals=[],
            quality="",
            confidence=0.0,
            failure=True,
            failure_reason="File not found",
            processor_version="1.0",
        )
        
    file_hash = _hash_file(full_path)
    
    if media_type == "audio":
        model_name = DEFAULT_GEMINI_MODEL if ASR_MODEL_NAME == "auto" else ASR_MODEL_NAME
    else:
        model_name = DEFAULT_GEMINI_MODEL if IMAGE_MODEL_NAME == "auto" else IMAGE_MODEL_NAME

    cache_key = f"{media_id}_{file_hash}_{LLM_PROVIDER}_{model_name}_{_PROMPT_VERSION}"
    
    cache = _load_cache()
    if cache_key in cache:
        return MediaAnalysis(**cache[cache_key])

    # Check if we actually have API Keys. If not, mock the failure cleanly.
    if not GEMINI_API_KEY:
        return MediaAnalysis(
            media_id=media_id,
            media_type=media_type,
            extracted_text="",
            summary="Media omitted due to missing API provider",
            language="en",
            urgency_signals=[],
            risk_signals=[],
            promotion_signals=[],
            event_signals=[],
            quality="low",
            confidence=0.0,
            failure=True,
            failure_reason="No API keys present",
            processor_version="1.0"
        )

    try:
        from google import genai
        from google.genai import types
        from google.genai.errors import APIError
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        _pace()
        
        # We need to upload the file to gemini API
        uploaded_file = client.files.upload(file=str(full_path))
        
        prompt = (
            "Extract structured information from this media file. "
            "Provide OCR text or transcript, a summary, the language used, "
            "and any urgency, risk, promotion, or event signals."
        )
        
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[uploaded_file, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.0
                    )
                )
                break
            except APIError as api_err:
                if api_err.code == 429:
                    raise Exception("Rate limit (429) on media extraction.")
                if attempt == 1:
                    raise
                _pace()
                
        raw_json = response.text
        parsed = json.loads(raw_json)
        
        analysis = MediaAnalysis(
            media_id=media_id,
            media_type=media_type,
            extracted_text=parsed.get("extracted_text", ""),
            summary=parsed.get("summary", ""),
            language=parsed.get("language", ""),
            urgency_signals=parsed.get("urgency_signals", []),
            risk_signals=parsed.get("risk_signals", []),
            promotion_signals=parsed.get("promotion_signals", []),
            event_signals=parsed.get("event_signals", []),
            quality=parsed.get("quality", "high"),
            confidence=float(parsed.get("confidence", 0.8)),
            failure=False,
            failure_reason="",
            processor_version="1.1"
        )
        
        cache[cache_key] = analysis.__dict__
        _save_cache(cache)
        return analysis

    except Exception as e:
        analysis = MediaAnalysis(
            media_id=media_id,
            media_type=media_type,
            extracted_text="",
            summary="",
            language="",
            urgency_signals=[],
            risk_signals=[],
            promotion_signals=[],
            event_signals=[],
            quality="",
            confidence=0.0,
            failure=True,
            failure_reason=str(e),
            processor_version="1.1"
        )
        # Note: We do not cache failures so they can be retried on next run
        return analysis
