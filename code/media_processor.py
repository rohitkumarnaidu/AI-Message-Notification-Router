"""
Media Processor - Rate limit safe, resumable, caching processor for images and audio.
Delegates to unified provider interface in Phase 8/10.
"""
import os
import json
import hashlib
from pathlib import Path
from schemas import MediaAnalysis, ImageAnalysis
from config import CACHE_DIR
import provider
from PIL import Image

_CACHE_FILE = Path(CACHE_DIR) / "media_cache.json"
_PROMPT_VERSION = "p10v1"  # bumped for Phase 10 structured outputs

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
    """Process an image or voice note, returning a structured MediaAnalysis or ImageAnalysis."""
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

    # Lightweight validation using PIL for images
    if media_type == "image":
        try:
            with Image.open(full_path) as img:
                img.verify()
        except Exception as e:
            return ImageAnalysis(
                media_id=media_id,
                media_type=media_type,
                extracted_text="",
                summary="",
                language="",
                urgency_signals=[],
                risk_signals=[],
                promotion_signals=[],
                event_signals=[],
                quality="corrupt",
                confidence=0.0,
                failure=True,
                failure_reason=f"Invalid image file: {e}",
                processor_version=_PROMPT_VERSION
            )

    file_hash = _hash_file(full_path)
    
    cache_key = f"{media_id}_{file_hash}_{_PROMPT_VERSION}_{media_type}"
    
    cache = _load_cache()
    if cache_key in cache:
        if media_type == "image":
            return ImageAnalysis(**cache[cache_key])
        return MediaAnalysis(**cache[cache_key])

    try:
        if media_type == "audio":
            analysis = provider.transcribe_audio(str(full_path))
            
            # If it's a MediaAnalysis object (like transcribed audio returning a dataclass)
            if hasattr(analysis, "extracted_text"):
                extracted = analysis.extracted_text.lower()
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
                    quality="high" if analysis.success else "low",
                    confidence=0.9 if analysis.success else 0.0,
                    failure=not analysis.success,
                    failure_reason=analysis.failure_category or "",
                    processor_version=_PROMPT_VERSION,
                    provider=analysis.provider,
                    model=analysis.model,
                    operation=analysis.operation,
                    attempts=analysis.attempts,
                    latency=analysis.latency,
                    success=analysis.success,
                    failure_category=analysis.failure_category
                )
            else:
                raise ValueError("Transcribe audio returned unexpected format")
        else:
            analysis = provider.analyze_image(str(full_path))
            # analysis is a dict conforming to ImageAnalysisResponse
            ocr = analysis.get("ocr_text", "").lower()
            vis = analysis.get("visual_summary", "").lower()
            
            urgency_signals = ["urgent"] if "urgent" in ocr or "now" in ocr else []
            risk_signals = ["scam"] if "password" in ocr or "otp" in ocr else []
            if analysis.get("has_financial_elements"):
                risk_signals.append("financial_elements")
            
            promotion_signals = ["promo"] if analysis.get("has_promotional_elements") else []
            event_signals = ["event"] if "tomorrow" in ocr else []
            
            if analysis.get("has_qr_code"):
                risk_signals.append("qr_code")

            final_analysis = ImageAnalysis(
                media_id=media_id,
                media_type=media_type,
                extracted_text=ocr,
                summary=vis,
                language="en",
                urgency_signals=urgency_signals,
                risk_signals=risk_signals,
                promotion_signals=promotion_signals,
                event_signals=event_signals,
                quality="high" if analysis.get("success") else "low",
                confidence=analysis.get("confidence", 0.8),
                failure=not analysis.get("success", False),
                failure_reason=analysis.get("failure_category", ""),
                processor_version=_PROMPT_VERSION,
                provider=analysis.get("provider", ""),
                model=analysis.get("model", ""),
                operation=analysis.get("operation", ""),
                attempts=analysis.get("attempts", 0),
                latency=analysis.get("latency", 0.0),
                success=analysis.get("success", False),
                failure_category=analysis.get("failure_category"),
                ocr_text=analysis.get("ocr_text", ""),
                visual_summary=analysis.get("visual_summary", ""),
                has_qr_code=analysis.get("has_qr_code", False),
                has_financial_elements=analysis.get("has_financial_elements", False),
                has_promotional_elements=analysis.get("has_promotional_elements", False),
                is_prompt_injection=analysis.get("is_prompt_injection", False)
            )

        if final_analysis.success:
            cache[cache_key] = final_analysis.__dict__
            _save_cache(cache)
            
        return final_analysis

    except Exception as e:
        if media_type == "image":
            return ImageAnalysis(
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
        else:
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
