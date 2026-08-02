"""
Phase 8 Provider — Multi-Provider failover, resilient network handling, rate limiting.

Supports NVIDIA, Groq, and Gemini.
"""
import os
import json
import time
import random
import hashlib
from typing import TypedDict, Optional, List, Dict, Any
from pathlib import Path
import httpx

from config import (
    LLM_MODEL_ID,
    GEMINI_API_KEY,
    GROQ_API_KEY,
    DEFAULT_GEMINI_MODEL,
    CACHE_DIR,
)
from schemas import RouterDecision

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")

class MediaAnalysis(TypedDict):
    provider: str
    model: str
    operation: str
    attempts: int
    latency: float
    success: bool
    failure_category: Optional[str]
    extracted_text: Optional[str]

class ProviderFallbackError(Exception):
    """Raised when the API is unavailable or quota is exhausted."""
    pass

class PolicyRejectionError(Exception):
    """Raised when the provider rejects the prompt due to safety policy."""
    def __init__(self, reason: str):
        super().__init__(f"Provider policy rejection: {reason}")
        self.reason = reason

class SchemaValidationError(Exception):
    """Raised when the LLM output violates the required JSON schema."""
    pass


# ---------------------------------------------------------------------------
# Quota Schedulers
# ---------------------------------------------------------------------------

class QuotaScheduler:
    def __init__(self, min_spacing: float):
        self.last_call_time = 0.0
        self.min_spacing = min_spacing
        
    def pace(self):
        elapsed = time.monotonic() - self.last_call_time
        wait = self.min_spacing - elapsed
        if wait > 0:
            time.sleep(wait)
        self.last_call_time = time.monotonic()
        
    def record_call(self):
        pass

# NVIDIA 40 RPM => 1.5s spacing, we use 2.5s to be safe
nvidia_scheduler = QuotaScheduler(2.5)
# Groq rate limits are typically 30 RPM for Llama3 => 2.0s
groq_scheduler = QuotaScheduler(2.0)
# Gemini 15 RPM => 4.0s
gemini_scheduler = QuotaScheduler(4.0)


# ---------------------------------------------------------------------------
# Error Classification
# ---------------------------------------------------------------------------

def classify_http_error(status_code: int, exc_str: str) -> str:
    exc_str = exc_str.lower()
    if status_code == 429:
        return "RATE_LIMIT"
    elif status_code in (401, 403):
        return "AUTHENTICATION"
    elif status_code == 404:
        return "MODEL_NOT_FOUND"
    elif status_code == 400 and ("policy" in exc_str or "safety" in exc_str):
        return "PROVIDER_POLICY_REJECTION"
    elif status_code >= 500:
        return "SERVER_ERROR"
    elif status_code >= 400:
        return "PERMANENT_CLIENT_ERROR"
    
    if "timeout" in exc_str or "connection" in exc_str or "winerror 10060" in exc_str or "eof" in exc_str:
        return "TRANSIENT_NETWORK"
        
    return "UNKNOWN"


def _validate_parsed(parsed: dict, allowed_evidence: List[str] = None) -> dict:
    ALLOWED_ACTIONS = {"notify", "digest", "mute"}
    ALLOWED_TYPES = {
        "personal", "urgent", "event", "payment", "business_update",
        "promotion", "greeting", "forward", "spam", "scam", "unknown",
    }
    
    action = parsed.get("action")
    if action not in ALLOWED_ACTIONS:
        raise SchemaValidationError(f"Invalid action: {action!r}")

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

    ev = parsed.get("evidence_message_ids", [])
    if not isinstance(ev, list):
        ev = []
        
    valid_ev = []
    if allowed_evidence:
        for e in ev:
            if e in allowed_evidence:
                valid_ev.append(e)
    else:
        valid_ev = ev
        
    parsed["evidence_message_ids"] = valid_ev
    return parsed

# ---------------------------------------------------------------------------
# Provider Implementations (Routing)
# ---------------------------------------------------------------------------

def call_nvidia(prompt: str, evidence_allowlist: List[str]) -> RouterDecision:
    import openai
    model = "meta/llama-3.1-70b-instruct"
    
    if not NVIDIA_API_KEY:
        raise ProviderFallbackError("NVIDIA_API_KEY not configured")
        
    client = openai.OpenAI(
        api_key=NVIDIA_API_KEY, 
        base_url="https://integrate.api.nvidia.com/v1", 
        max_retries=0,
        timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)
    )
    
    start_time = time.monotonic()
    attempts = 0
    
    messages = [
        {"role": "system", "content": "You are a routing system. You must output valid JSON. Use this schema: {\"action\": \"notify|digest|mute\", \"message_type\": \"...\", \"reason\": \"...\", \"confidence\": 0.0, \"evidence_message_ids\": []}"},
        {"role": "user", "content": prompt}
    ]
    
    for attempt in range(3):
        attempts += 1
        nvidia_scheduler.pace()
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            nvidia_scheduler.record_call()
            content = resp.choices[0].message.content
            parsed = json.loads(content)
            parsed = _validate_parsed(parsed, evidence_allowlist)
            
            latency = time.monotonic() - start_time
            return RouterDecision(
                provider="NVIDIA",
                model=model,
                operation="generate_routing_decision",
                attempts=attempts,
                latency=latency,
                success=True,
                failure_category=None,
                structured_output_status="valid",
                action=parsed["action"],
                message_type=parsed["message_type"],
                reason=parsed.get("reason"),
                confidence=parsed.get("confidence"),
                evidence_message_ids=parsed.get("evidence_message_ids"),
                decision_signals=parsed.get("decision_signals", []),
                uncertainties=parsed.get("uncertainties", [])
            )
            
        except (openai.APITimeoutError, openai.APIConnectionError) as e:
            if attempt < 2:
                time.sleep((2 ** attempt) + random.uniform(0, 1))
                continue
            raise ProviderFallbackError(f"NVIDIA Network Error: {e}")
        except openai.APIError as e:
            cat = classify_http_error(getattr(e, 'status_code', 500), str(e))
            if cat == "PROVIDER_POLICY_REJECTION":
                raise PolicyRejectionError(str(e))
            if cat in ("TRANSIENT_NETWORK", "RATE_LIMIT", "SERVER_ERROR") and attempt < 2:
                time.sleep((2 ** attempt) + random.uniform(0, 1))
                continue
            raise ProviderFallbackError(f"NVIDIA API Error: {e}")
        except (openai.APITimeoutError, openai.APIConnectionError) as e:
            if attempt < 2:
                time.sleep((2 ** attempt) + random.uniform(0, 1))
                continue
            raise ProviderFallbackError(f"NVIDIA Network Error: {e}")
        except (json.JSONDecodeError, SchemaValidationError) as e:
            if attempt < 1:
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": f"Schema validation failed: {e}. Return ONLY valid JSON."})
                continue
            raise ProviderFallbackError(f"NVIDIA Schema Error: {e}")
            
    raise ProviderFallbackError("NVIDIA failed after retries")


def call_groq(prompt: str, evidence_allowlist: List[str]) -> RouterDecision:
    import openai
    model = "llama-3.3-70b-versatile"
    
    if not GROQ_API_KEY:
        raise ProviderFallbackError("GROQ_API_KEY not configured")
        
    client = openai.OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        max_retries=0,
        timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)
    )
    
    start_time = time.monotonic()
    attempts = 0
    
    messages = [
        {"role": "system", "content": "You are a routing system. You must output valid JSON. Use this schema: {\"action\": \"notify|digest|mute\", \"message_type\": \"...\", \"reason\": \"...\", \"confidence\": 0.0, \"evidence_message_ids\": []}"},
        {"role": "user", "content": prompt}
    ]
    
    for attempt in range(3):
        attempts += 1
        groq_scheduler.pace()
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            groq_scheduler.record_call()
            content = resp.choices[0].message.content
            parsed = json.loads(content)
            parsed = _validate_parsed(parsed, evidence_allowlist)
            
            latency = time.monotonic() - start_time
            return RouterDecision(
                provider="Groq",
                model=model,
                operation="generate_routing_decision",
                attempts=attempts,
                latency=latency,
                success=True,
                failure_category=None,
                structured_output_status="valid",
                action=parsed["action"],
                message_type=parsed["message_type"],
                reason=parsed.get("reason"),
                confidence=parsed.get("confidence"),
                evidence_message_ids=parsed.get("evidence_message_ids"),
                decision_signals=parsed.get("decision_signals", []),
                uncertainties=parsed.get("uncertainties", [])
            )
            
        except (openai.APITimeoutError, openai.APIConnectionError) as e:
            if attempt < 2:
                time.sleep((2 ** attempt) + random.uniform(0, 1))
                continue
            raise ProviderFallbackError(f"Groq Network Error: {e}")
        except openai.APIError as e:
            cat = classify_http_error(getattr(e, 'status_code', 500), str(e))
            if cat == "PROVIDER_POLICY_REJECTION":
                raise PolicyRejectionError(str(e))
            if cat in ("TRANSIENT_NETWORK", "RATE_LIMIT", "SERVER_ERROR") and attempt < 2:
                time.sleep((2 ** attempt) + random.uniform(0, 1))
                continue
            raise ProviderFallbackError(f"Groq API Error: {e}")
        except (json.JSONDecodeError, SchemaValidationError) as e:
            if attempt < 1:
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": f"Schema validation failed: {e}. Return ONLY valid JSON."})
                continue
            raise ProviderFallbackError(f"Groq Schema Error: {e}")
            
    raise ProviderFallbackError("Groq failed after retries")


def call_gemini(prompt: str, evidence_allowlist: List[str]) -> RouterDecision:
    from google import genai
    from google.genai import types
    from google.genai.errors import APIError
    
    model = DEFAULT_GEMINI_MODEL
    
    if not GEMINI_API_KEY:
        raise ProviderFallbackError("GEMINI_API_KEY not configured")
        
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    start_time = time.monotonic()
    attempts = 0
    
    current_prompt = prompt
    
    for attempt in range(3):
        attempts += 1
        gemini_scheduler.pace()
        try:
            response = client.models.generate_content(
                model=model,
                contents=current_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )
            gemini_scheduler.record_call()
            
            if response.candidates and response.candidates[0].finish_reason:
                fr = response.candidates[0].finish_reason
                if fr.name in ("SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT"):
                    raise PolicyRejectionError(fr.name)
            
            if not response.text:
                raise ProviderFallbackError("Empty response returned by Gemini.")
                
            parsed = json.loads(response.text)
            parsed = _validate_parsed(parsed, evidence_allowlist)
            
            latency = time.monotonic() - start_time
            return RouterDecision(
                provider="Gemini",
                model=model,
                operation="generate_routing_decision",
                attempts=attempts,
                latency=latency,
                success=True,
                failure_category=None,
                structured_output_status="valid",
                action=parsed["action"],
                message_type=parsed["message_type"],
                reason=parsed.get("reason"),
                confidence=parsed.get("confidence"),
                evidence_message_ids=parsed.get("evidence_message_ids"),
                decision_signals=parsed.get("decision_signals", []),
                uncertainties=parsed.get("uncertainties", [])
            )
            
        except APIError as api_err:
            cat = classify_http_error(api_err.code, str(api_err))
            if cat == "PROVIDER_POLICY_REJECTION":
                raise PolicyRejectionError(str(api_err))
            if cat in ("TRANSIENT_NETWORK", "RATE_LIMIT", "SERVER_ERROR") and attempt < 2:
                time.sleep((2 ** attempt) + random.uniform(0, 1))
                continue
            raise ProviderFallbackError(f"Gemini API error: {api_err}")
        except Exception as e:
            exc_str = str(e).lower()
            if "timeout" in exc_str or "connection" in exc_str or "winerror 10060" in exc_str or "eof" in exc_str:
                if attempt < 2:
                    time.sleep((2 ** attempt) + random.uniform(0, 1))
                    continue
            if isinstance(e, (json.JSONDecodeError, SchemaValidationError)):
                if attempt < 1:
                    current_prompt += f"\n\nPREVIOUS OUTPUT ERROR: {e}. Return ONLY valid JSON."
                    continue
                raise ProviderFallbackError(f"Gemini Schema Error: {e}")
            raise ProviderFallbackError(f"Gemini Error: {e}")
            
    raise ProviderFallbackError("Gemini failed after retries")


def generate_routing_decision(prompt: str, evidence_allowlist: List[str] = None) -> RouterDecision:
    """Entry point routing logic using fallback chain: NVIDIA -> Groq."""
    try:
        return call_nvidia(prompt, evidence_allowlist)
    except PolicyRejectionError:
        raise
    except ProviderFallbackError as e:
        print(f"NVIDIA Fallback: {e}")
        
    try:
        return call_groq(prompt, evidence_allowlist)
    except PolicyRejectionError:
        raise
    except ProviderFallbackError as e:
        print(f"Groq Fallback: {e}")
        raise

# ---------------------------------------------------------------------------
# Provider Implementations (Media)
# ---------------------------------------------------------------------------

def analyze_image(path: str) -> MediaAnalysis:
    from google import genai
    from google.genai import types
    
    if not GEMINI_API_KEY:
        raise ProviderFallbackError("GEMINI_API_KEY not configured")

    client = genai.Client(api_key=GEMINI_API_KEY)
    start_time = time.monotonic()
    
    try:
        gemini_scheduler.pace()
        myfile = client.files.upload(file=path)
        gemini_scheduler.record_call()
        
        prompt = "Extract all text and describe the key visual elements. Output in JSON: {\"extracted_text\": \"...\", \"detected_objects\": []}"
        
        gemini_scheduler.pace()
        response = client.models.generate_content(
            model=DEFAULT_GEMINI_MODEL,
            contents=[myfile, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.0)
        )
        gemini_scheduler.record_call()
        
        parsed = json.loads(response.text)
        return MediaAnalysis(
            provider="Gemini",
            model=DEFAULT_GEMINI_MODEL,
            operation="analyze_image",
            attempts=1,
            latency=time.monotonic() - start_time,
            success=True,
            failure_category=None,
            extracted_text=parsed.get("extracted_text", "") + " " + " ".join(parsed.get("detected_objects", []))
        )
    except Exception as e:
        raise ProviderFallbackError(f"Gemini Image Error: {e}")

def transcribe_audio(path: str) -> MediaAnalysis:
    import openai
    
    start_time = time.monotonic()
    
    # Try Groq
    try:
        if not GROQ_API_KEY:
            raise ProviderFallbackError("GROQ_API_KEY not configured")
        client = openai.OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            max_retries=1
        )
        groq_scheduler.pace()
        with open(path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                file=(path, f.read()),
                model="whisper-large-v3-turbo"
            )
        groq_scheduler.record_call()
        return MediaAnalysis(
            provider="Groq",
            model="whisper-large-v3-turbo",
            operation="transcribe_audio",
            attempts=1,
            latency=time.monotonic() - start_time,
            success=True,
            failure_category=None,
            extracted_text=transcription.text
        )
    except Exception as e:
        print(f"Groq Audio Fallback: {e}")
        
    # Try Gemini
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        gemini_scheduler.pace()
        myfile = client.files.upload(file=path)
        gemini_scheduler.record_call()
        
        gemini_scheduler.pace()
        response = client.models.generate_content(
            model=DEFAULT_GEMINI_MODEL,
            contents=[myfile, "Transcribe this audio strictly."]
        )
        gemini_scheduler.record_call()
        return MediaAnalysis(
            provider="Gemini",
            model=DEFAULT_GEMINI_MODEL,
            operation="transcribe_audio",
            attempts=1,
            latency=time.monotonic() - start_time,
            success=True,
            failure_category=None,
            extracted_text=response.text
        )
    except Exception as e:
        raise ProviderFallbackError(f"Gemini Audio Error: {e}")

