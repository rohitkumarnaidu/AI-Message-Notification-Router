# Multimodal Processing Defense

Image Pipeline:
- PIL pre-validation, MD5 caching, Gemini 2.5 Flash OCR and visual summaries.
- OCR text wrapped in untrusted tags for prompt injection isolation.

Voice Pipeline:
- Groq Whisper ASR (whisper-large-v3-turbo) with Gemini fallback.
- Hinglish transliterated safety normalization (e.g. otpee -> OTP).
