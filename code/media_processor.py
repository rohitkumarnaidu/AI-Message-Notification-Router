"""
Media Processor - Rate limit safe, resumable, caching processor for images and audio.
Delegates to unified provider interface in Phase 8/10.
"""
import os
import json
import hashlib
import time
from pathlib import Path
from schemas import MediaAnalysis, ImageAnalysis, VoiceAnalysis
from config import CACHE_DIR
import provider
from PIL import Image

_CACHE_FILE = Path(CACHE_DIR) / "media_cache.json"
_PROMPT_VERSION = "p11v1"  # bumped for Phase 11 voice handling

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
        elif media_type in ("voice", "audio", "voice_note"):
            return VoiceAnalysis(**cache[cache_key])
        return MediaAnalysis(**cache[cache_key])

    try:
        if media_type in ("voice", "audio", "voice_note"):
            analysis = provider.transcribe_audio(str(full_path))
            
            # If it's a dict
            if isinstance(analysis, dict) and "extracted_text" in analysis:
                extracted = analysis["extracted_text"].lower()
                
                # Use regexes from feature_extractor to parse risk signals from audio
                from feature_extractor import (
                    _OTP_REQUEST, _CREDENTIAL_REQUEST, _PAYMENT_PRESSURE,
                    _ACCOUNT_BLOCK_THREAT, _PROMPT_INJECTION, _PROMOTION_LANGUAGE,
                    _FINANCIAL_DATA, _IMMEDIATE_TIME, _DEADLINE, _WAITING_SIGNAL
                )
                
                contains_otp = bool(_OTP_REQUEST.search(extracted))
                contains_cred = bool(_CREDENTIAL_REQUEST.search(extracted))
                contains_payment = bool(_PAYMENT_PRESSURE.search(extracted))
                contains_block = bool(_ACCOUNT_BLOCK_THREAT.search(extracted))
                contains_injection = bool(_PROMPT_INJECTION.search(extracted))
                contains_promo = bool(_PROMOTION_LANGUAGE.search(extracted))
                contains_financial = bool(_FINANCIAL_DATA.search(extracted))
                contains_urgent = bool(_IMMEDIATE_TIME.search(extracted)) or bool(_DEADLINE.search(extracted)) or bool(_WAITING_SIGNAL.search(extracted)) or "urgent" in extracted
                
                risk_signals = []
                if contains_otp or contains_cred or contains_block or contains_payment or contains_financial:
                    risk_signals.append("scam")
                    
                urgency_signals = ["urgent"] if contains_urgent else []
                promotion_signals = ["promo"] if contains_promo else []
                
                final_analysis = VoiceAnalysis(
                    media_id=media_id,
                    media_type=media_type,
                    extracted_text=extracted,
                    summary=extracted[:200],
                    language="en",
                    urgency_signals=urgency_signals,
                    risk_signals=risk_signals,
                    promotion_signals=promotion_signals,
                    event_signals=[],
                    quality="high" if analysis.get("success") else "low",
                    confidence=0.9 if analysis.get("success") else 0.0,
                    failure=not analysis.get("success"),
                    failure_reason=analysis.get("failure_category") or "",
                    processor_version=_PROMPT_VERSION,
                    provider=analysis.get("provider", ""),
                    model=analysis.get("model", ""),
                    operation=analysis.get("operation", ""),
                    attempts=analysis.get("attempts", 0),
                    latency=analysis.get("latency", 0.0),
                    success=analysis.get("success", False),
                    failure_category=analysis.get("failure_category"),
                    transcript=analysis.get("extracted_text", ""),
                    detected_language="en",
                    has_financial_elements=contains_financial or contains_payment,
                    has_promotional_elements=contains_promo,
                    is_prompt_injection=contains_injection,
                    contains_otp_request=contains_otp,
                    contains_credential_request=contains_cred,
                    contains_urgent_language=contains_urgent
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
