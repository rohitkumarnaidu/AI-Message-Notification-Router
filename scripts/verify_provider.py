"""
Phase 7 Provider Verification Script.
Tests live authentication and model identity.
Reports only: key configured, auth result, model used.
Never logs key values.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))
from config import GEMINI_API_KEY, FORCE_DETERMINISTIC_FALLBACK, LLM_PROVIDER, LLM_MODEL_ID

print(f"GEMINI_API_KEY configured: {bool(GEMINI_API_KEY and len(GEMINI_API_KEY) > 10)}")
print(f"GROQ_API_KEY configured: false")  # not used
print(f"FORCE_DETERMINISTIC_FALLBACK: {FORCE_DETERMINISTIC_FALLBACK}")
print(f"LLM_PROVIDER: {LLM_PROVIDER}")
print(f"LLM_MODEL_ID config: {LLM_MODEL_ID}")

if FORCE_DETERMINISTIC_FALLBACK:
    print("Provider authentication: SKIPPED (forced fallback)")
    sys.exit(0)

# Try each model candidate
candidates = ["gemini-2.0-flash-lite", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-3.5-flash"]
if LLM_MODEL_ID != "auto":
    candidates = [LLM_MODEL_ID] + candidates

from google import genai
from google.genai import types
from google.genai.errors import APIError

client = genai.Client(api_key=GEMINI_API_KEY)

test_prompt = 'Return exactly this JSON object: {"action": "notify", "message_type": "urgent", "reason": "test", "confidence": 0.9, "evidence_message_ids": []}'

for model in candidates:
    try:
        response = client.models.generate_content(
            model=model,
            contents=test_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0
            )
        )
        parsed = json.loads(response.text)
        print(f"\nProvider authentication: SUCCESS")
        print(f"Verified model identifier: {model}")
        print(f"SDK package: google-genai")
        print(f"Structured output returned: action={parsed.get('action')}")
        # update config recommendation
        if model != "gemini-3.5-flash":
            print(f"RECOMMENDATION: Update .env LLM_MODEL_ID={model} (gemini-3.5-flash does not exist)")
        break
    except APIError as e:
        if e.code == 429:
            print(f"Model {model}: RATE LIMITED (429) - quota exceeded")
        elif e.code == 404:
            print(f"Model {model}: NOT FOUND (404)")
        else:
            print(f"Model {model}: API ERROR {e.code}: {str(e)[:80]}")
    except Exception as e:
        print(f"Model {model}: ERROR: {str(e)[:120]}")
