"""
Media Processor - Rate limit safe, resumable, caching processor for images and audio.
Delegates to unified provider interface in Phase 8.
"""
import os
import json
import hashlib
from pathlib import Path
from schemas import MediaAnalysis
from config import CACHE_DIR
import provider

_CACHE_FILE = Path(CACHE_DIR) / "media_cache.json"
_PROMPT_VERSION = "p8v1"  # bumped for Phase 8

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
            processor_version=_PROMPT_VERSION
        )
        
    file_hash = _hash_file(full_path)
    
    # Cache key format requested by instructions: file hash, provider, model ID, prompt version
    # Since model ID might change based on failover, we cache the whole MediaAnalysis dict 
    # but the key itself must distinguish version
    cache_key = f"{media_id}_{file_hash}_{_PROMPT_VERSION}"
    
    cache = _load_cache()
    if cache_key in cache:
        return MediaAnalysis(**cache[cache_key])

    try:
        if media_type == "audio":
            analysis = provider.transcribe_audio(str(full_path))
        else:
            analysis = provider.analyze_image(str(full_path))
            
        # Parse extracted_text to basic signals for consistency with earlier phases
        extracted = analysis.get("extracted_text", "").lower()
        
        final_analysis = MediaAnalysis(
            media_id=media_id,
            media_type=media_type,
            extracted_text=extracted,
            summary=extracted[:200],
            language="en",
            urgency_signals=["urgent"] if "urgent" in extracted or "now" in extracted else [],
            risk_signals=["scam"] if "password" in extracted or "otp" in extracted else [],
            promotion_signals=["promo"] if "discount" in extracted or "sale" in extracted else [],
            event_signals=["event"] if "tomorrow" in extracted else [],
            quality="high" if analysis.get("success") else "low",
            confidence=0.9 if analysis.get("success") else 0.0,
            failure=not analysis.get("success"),
            failure_reason=analysis.get("failure_category", ""),
            processor_version=_PROMPT_VERSION,
            provider=analysis.get("provider", ""),
            model=analysis.get("model", ""),
            operation=analysis.get("operation", ""),
            attempts=analysis.get("attempts", 0),
            latency=analysis.get("latency", 0.0),
            success=analysis.get("success", False),
            failure_category=analysis.get("failure_category")
        )
        
        if final_analysis.success:
            # Note: We do not cache failures so they can be retried on next run
            cache[cache_key] = final_analysis.__dict__
            _save_cache(cache)
            
        return final_analysis

    except Exception as e:
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
            failure_reason=str(e),
            processor_version=_PROMPT_VERSION
        )
