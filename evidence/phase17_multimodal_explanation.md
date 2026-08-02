# Phase 17 Multimodal Explanation: Image & Voice Signal Processing

## Executive Overview
WhatsApp notification routing cannot rely on text alone. Users routinely receive screenshot notices, promotional event posters, payment QR codes, bank receipts, and voice notes. A robust router must inspect raw binary media files (`dataset/media/images/`, `dataset/media/audio/`) directly, extract grounded visual and acoustic signals, and integrate these signals into the core safety and interruption pipeline.

Our architecture features a **Resilient Multimodal Processing Engine** ([`code/media_processor.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/media_processor.py)) that handles both images and voice notes with rate-limit safety, MD5 content caching, schema validation, and defensive fallback.

---

## 1. Image Processing Pipeline Architecture

```
[Media ID & File Path] -> [PIL Pre-Validation] -> [MD5 Content Hash Check]
                                                          |
                      +-----------------------------------+-----------------------------------+
                      | (Cache Hit)                                                           | (Cache Miss)
                      v                                                                       v
          [Return Cached ImageAnalysis]                                   [Gemini Multimodal Structured API]
                                                                                              |
                                                                                              v
                                                                                  [Extract Visual Signals]
                                                                                   - OCR Text Extraction
                                                                                   - Visual Summary
                                                                                   - QR Code Presence
                                                                                   - Financial Elements
                                                                                   - Promotional Elements
                                                                                   - Visual Prompt Injection
                                                                                              |
                                                                                              v
                                                                                [Persist to media_cache.json]
```

### 1.1 Image Validation & Lightweight Inspection
Before making external API calls, [`code/media_processor.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/media_processor.py#L63-L84) performs lightweight pre-validation using Python's `PIL.Image`:
* Verifies file existence at `dataset/media/images/<filename>`.
* Invokes `img.verify()` to check structural image integrity.
* If file is missing or corrupted, returns an `ImageAnalysis` object with `failure=True`, `quality="corrupt"`, and `failure_reason="Invalid image file"`.

### 1.2 MD5 Content Hashing & Caching
To prevent redundant API costs and ensure deterministic re-runs:
* Computes an MD5 checksum over raw binary bytes (`_hash_file()`).
* Constructs a composite cache key: `{media_id}_{md5_hash}_{prompt_version}_image`.
* Checks `.cache/media_cache.json`. If cached, returns structured `ImageAnalysis` immediately in <1ms.

### 1.3 Gemini Multimodal Structured Analysis (`code/provider.py`)
For cache misses, `provider.analyze_image()` calls Google Gemini (`gemini-2.5-flash`) using Pydantic structured output constraints (`ImageAnalysisResponse`):
```python
class ImageAnalysisResponse(BaseModel):
    ocr_text: str = Field(description="Exact text extracted from the image.")
    visual_summary: str = Field(description="Descriptive summary of visual elements.")
    has_qr_code: bool = Field(description="True if a QR code is visually present.")
    has_financial_elements: bool = Field(description="True if credit cards/bank logos/UPI apps are visible.")
    has_promotional_elements: bool = Field(description="True if discount tags or sale banners are visible.")
    is_prompt_injection: bool = Field(description="True if image text contains AI override instructions.")
    confidence: float = Field(description="Confidence in visual analysis (0.0 to 1.0).")
```

### 1.4 Downstream Safety & Policy Overrides for Images
Visual signals directly trigger deterministic overrides in [`code/router.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/router.py#L253-L282):
* **Visual Prompt Injection**: If `is_prompt_injection=True`, action is forced to `mute`, message type to `scam`.
* **Unverified QR Payment**: If `has_financial_elements=True` or `has_qr_code=True` and sender is unverified, action is forced to `mute` (scam defense).
* **Unsubscribed Poster Promotion**: If `has_promotional_elements=True` without user opt-in, action is downgraded to `digest`.
* **Trusted Sender Image**: If a trusted contact sends a pure photo without caption, action is set to `notify` / `personal`.

---

## 2. Voice & Audio Processing Pipeline Architecture

```
[Voice Note File Path] -> [File Existence & Hash Check] -> [Cache Lookup]
                                                                  |
                      +-----------------------------------+-------+
                      | (Cache Hit)                       | (Cache Miss)
                      v                                   v
          [Return Cached VoiceAnalysis]       [Primary ASR: Groq Whisper-Large-v3-Turbo]
                                                          |
                                                          | (Fallback on Error/Timeout)
                                                          v
                                              [Secondary ASR: Gemini 2.5 Flash]
                                                          |
                                                          v
                                              [Multilingual Normalization]
                                              (Hindi/Hinglish Transliteration)
                                                          |
                                                          v
                                              [Regex Feature Extraction]
                                               - OTP / Credential Request
                                               - Urgent Time Language
                                               - Financial / Payment Pressure
```

### 2.1 Resilient Multi-Provider ASR Engine (`code/provider.py`)
Voice notes (`dataset/media/audio/`) are processed using a tiered provider chain:
1. **Primary ASR**: Groq Whisper (`whisper-large-v3-turbo`) via `client.audio.transcriptions.create()`. Offers state-of-the-art speed and accuracy for conversational speech.
2. **Secondary ASR**: Google Gemini (`gemini-2.5-flash`) via `client.files.upload()`. Triggered automatically if Groq encounters rate limits or network errors.

### 2.2 Multilingual Normalization & Transliteration (`code/multilingual_safety.py`)
WhatsApp voice notes in India frequently mix English, Hindi, and Hinglish. Audio transcripts are normalized via `normalize_for_safety(text, apply_asr=True)`:
* **ASR Phonetic Correction**: Maps misheard phrases like `oh tee pee` -> `OTP`, `paasword` -> `password`, `share karna` -> `share`.
* **Hinglish Intent Detection**: Detects spoken Hindi urgency (`turant bhejo`, `jaldi karo`) and spoken credential demands (`apna otp batao`, `khata band ho jayega`).

### 2.3 Audio Feature Extraction & Safety Integration
Extracted transcripts are evaluated against grounded safety regexes ([`code/media_processor.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/media_processor.py#L112-L130)):
* **Spoken OTP / Credential Theft**: Triggers `contains_otp_request=True` or `contains_credential_request=True` -> forces `mute` / `scam`.
* **Spoken Payment Pressure**: Triggers `has_financial_elements=True` -> forces `mute` if sender is unverified.
* **Voice Prompt Injection**: Spoken commands attempting to manipulate the router logic -> forces `mute` / `scam`.

---

## 3. Comparative Summary: Media Types & Handling

| Media Type | Processing Engine | Key Signals Extracted | Safety & Routing Policy Impact |
|---|---|---|---|
| **Text Only** | Standard Pipeline | Text regexes, entity matching, historical signals | Preclassifier & baseline rules apply |
| **Image Poster / Screenshot** | PIL + Gemini 2.5 Flash Multimodal | OCR text, visual summary, QR code, financial items, promo banners, visual injection | Unverified QR -> `mute`; Promo banner -> `digest`; Visual injection -> `mute` |
| **Voice Note (Audio)** | Groq Whisper + Gemini Fallback + ASR Normalizer | Acoustic transcript, language, spoken OTP, financial pressure, Hinglish urgency | Spoken OTP -> `mute`; Spoken payment pressure -> `mute`; Spoken urgency -> `notify` |

---

## 4. Media Error Handling & Fallback Guarantees

In real-world deployment, media files may be missing, corrupt, truncated, or API rate limits may prevent visual processing. Our architecture guarantees **graceful degradation**:

1. **Non-Blocking Execution**: Media failures never throw uncaught exceptions or halt batch routing.
2. **Failure Payload Flagging**: Corrupted media returns a structured analysis with `failure=True` and `failure_reason`.
3. **Calibrated Confidence Penalty**: When media processing fails for a message with media present, [`code/confidence.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/confidence.py#L24) applies a mandatory `-0.15` confidence penalty.
4. **Unsafe-Notify Prevention**: If a proposed `notify` action depends on media content but media analysis failed, [`code/unsafe_notify_validator.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/unsafe_notify_validator.py#L123-L127) automatically downgrades the action from `notify` to `digest`.

---

## Summary Statement
By combining pre-validation, MD5 caching, structured multimodal LLM analysis, Groq Whisper ASR, and defensive fallback penalties, our multimodal engine processes image posters and voice notes safely, accurately, and resiliently.
