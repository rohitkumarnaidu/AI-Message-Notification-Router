# Phase 18: Reproducibility Handoff Specification

## 1. Executive Summary
This document specifies the complete environment, dataset, configuration, and execution requirements for end-to-end deterministic reproduction of the **HackerRank Orchestrate Message Notification Router** (August 2026). 

The system routes incoming multimodal WhatsApp messages (`notify`, `digest`, `mute`) using a hybrid deterministic-provider architecture with hard safety overrides, multi-provider API failover, media analysis (OCR and ASR), and strict output schema validation.

---

## 2. Environment & Version Metadata
- **Repository Commit**: `c74daa5ac33e5d0945cc72bc90d7a67599b189b8`
- **Python Version**: `3.14.6` (Tested on Windows 11 x64)
- **Primary Execution Entrypoint**: `code/main.py`
- **Encoding**: UTF-8 (Strict)

### Python Core Dependencies
The system relies on standard library utilities along with the following verified packages:
- `openai >= 1.0.0` (Client interface for NVIDIA & Groq provider endpoints)
- `google-genai >= 0.1.0` (Client interface for Google Gemini API)
- `httpx >= 0.27.0` (HTTP client & network timeout handling)
- `pillow >= 10.0.0` (Image validation and lightweight processing)
- `pytest >= 8.0.0` (Test execution harness)
- `python-dotenv >= 1.0.0` (Environment variable configuration loader)
- `pydantic >= 2.0.0` (Schema validation helper)

---

## 3. Dataset Layout & Directory Requirements
All input data files must reside inside the `dataset/` directory relative to the repository root:

```text
dataset/
├── messages.csv                  # Incoming messages to route (110 target rows)
├── output.csv                    # Evaluation submission template
├── sample_messages.csv           # Solved training & validation examples
├── users.csv                     # User profiles, quiet hours, & notification loads
├── groups.csv                    # Group chat metadata
├── group_members.csv             # User membership and admin roles in groups
├── business_accounts.csv         # Verified/unverified business account metadata
├── user_business_history.csv     # Transaction history & subscription status
├── message_history.csv           # Historical message archive for retrieval
├── message_events.csv            # Historical user actions (reply, dismiss, mute, report)
├── images.csv                    # Image ID mapping to file paths
├── voice_notes.csv               # Voice note ID mapping to file paths
├── daily_notification_summary.csv # User daily notification stats
└── media/                        # Raw media binary directory
    ├── images/                   # Image poster/screenshot files (.jpg, .png)
    └── audio/                    # Voice note audio files (.m4a, .mp3, .wav)
```

---

## 4. Environment Variables & API Key Configuration
Environment variables can be provided via system environment or loaded automatically from a `.env` file at the repository root:

| Variable Name | Purpose | Example Value / Default | Required for Offline Mode |
|---|---|---|---|
| `NVIDIA_API_KEY` | Primary text routing LLM (Llama-3.1-70B) | `nvapi-...` | No |
| `GROQ_API_KEY` | Secondary text routing & primary ASR (Whisper) | `gsk_...` | No |
| `GEMINI_API_KEY` | Image OCR/Visual analysis & fallback text | `AIzaSy...` | No |
| `FORCE_DETERMINISTIC_FALLBACK` | Forces 100% rule-based execution | `false` (Set `true` for offline) | N/A |
| `MODEL_PROVIDER` | Default text provider choice | `gemini` or `auto` | No |
| `MODEL_NAME` | Target LLM model ID | `gemini-3.5-flash` or `auto` | No |
| `MAX_REQUESTS_PER_MINUTE` | Provider API rate-pacing limit | `10` | No |
| `MIN_SECONDS_BETWEEN_CALLS` | Minimum sleep between API invocations | `7.0` | No |

---

## 5. Execution Commands

### 5.1 Environment Diagnostics & Data Pre-Check
To verify file integrity, schema correctness, and dataset completeness:
```bash
python code/main.py --check
```
*Expected Output*: `Phase 0 Diagnostic Check Completed Successfully. READY FOR PHASE 1.`

### 5.2 Test Suite Validation (Offline)
To execute the complete 118-test safety, policy, and quality verification suite:
```bash
python -m pytest tests/ -q
```
*Expected Output*: `118 passed in ~1.09s`

### 5.3 Full Production Candidate Generation
To run the hybrid pipeline over `dataset/messages.csv` and generate `output.csv`:
```bash
python code/main.py --run
```
*Output Destination*: `output.csv` (and archived copy in `outputs/phase15_release_candidate.csv`).

### 5.4 Solved Sample Validation
To test pipeline predictions against the solved benchmark dataset (`dataset/sample_messages.csv`):
```bash
python code/main.py --run --samples
```

---

## 6. Provider-Disabled Fallback & Resiliency
If API keys (`NVIDIA_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`) are missing, invalid, or rate-limited:
1. `config.py` automatically detects missing keys and forces `FORCE_DETERMINISTIC_FALLBACK = True`.
2. The pipeline gracefully falls back to `preclassifier.py` and `baseline_policy.py`.
3. High-certainty deterministic rules (credential protection, prompt injection, scam detection, greetings, verified promos) execute with 100% accuracy without raising unhandled exceptions or making network calls.

---

## 7. Checkpoint Resume & Caching Mechanics
To prevent redundant API calls and optimize re-run latency:
- **Media Cache**: Media analysis results (OCR, visual summary, ASR transcripts, risk signals) are cached in `.cache/media_cache.json`.
- **Cache Invalidation**: Cache entries use an MD5 hash of the raw media file combined with `media_id`, `media_type`, and prompt version `p11v1`.
- **Resumption**: Re-running `python code/main.py --run` reuses cached media analysis automatically, completing execution in seconds.
