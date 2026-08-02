from schemas import RouterDecision
from config import FORCE_DETERMINISTIC_FALLBACK, LLM_PROVIDER, LLM_MODEL_ID, GEMINI_API_KEY, GROQ_API_KEY
import json

class ProviderFallbackError(Exception):
    """Raised when the API is unavailable, times out, or keys are missing."""
    pass

class SchemaValidationError(Exception):
    """Raised when the LLM output violates the required JSON schema."""
    pass

def generate_structured_decision(prompt: str) -> RouterDecision:
    """
    Calls the configured LLM API.
    """
    if FORCE_DETERMINISTIC_FALLBACK:
        raise ProviderFallbackError("API Keys missing or deterministic fallback forced.")

    try:
        if LLM_PROVIDER == "gemini":
            from google import genai
            from google.genai import types
            
            # Using the new google-genai SDK
            client = genai.Client(api_key=GEMINI_API_KEY)
            
            # Use default model or specific one if provided
            model_name = "gemini-3.5-flash" if LLM_MODEL_ID == "auto" else LLM_MODEL_ID
            
            # Bounded retry attempt (Max 2 calls: 1 initial + 1 repair)
            for attempt in range(2):
                try:
                    # Set up schema response
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.0
                        )
                    )
                    raw_json = response.text
                    parsed = json.loads(raw_json)
                    
                    # Validate allowed enums and schema bounds
                    action = parsed.get("action")
                    if action not in ["notify", "digest", "mute"]:
                        raise SchemaValidationError(f"Invalid action: {action}")
                        
                    conf = parsed.get("confidence", 0.0)
                    if not (0.0 <= float(conf) <= 1.0):
                        raise SchemaValidationError(f"Invalid confidence: {conf}")
                    
                    return RouterDecision(**parsed)
                except (json.JSONDecodeError, SchemaValidationError, TypeError) as e:
                    if attempt == 1:
                        raise ProviderFallbackError(f"Schema repair failed after 2 attempts: {str(e)}")
                    # Append repair instructions to prompt for the second attempt
                    prompt += f"\n\nERROR IN PREVIOUS OUTPUT: {str(e)}. PLEASE FIX JSON OUTPUT AND ENSURE IT MATCHES SCHEMA STRICTLY."
            
        else:
            raise ProviderFallbackError(f"Unsupported provider: {LLM_PROVIDER}")

    except ProviderFallbackError:
        raise
    except Exception as e:
        raise ProviderFallbackError(f"SDK failure: {str(e)}")

