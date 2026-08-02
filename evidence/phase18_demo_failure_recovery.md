# Phase 18 Demo Failure Recovery Playbook

## Executive Overview
This document provides an **emergency troubleshooting and failure recovery manual** for 12 potential failure modes that could occur during live demonstration, judge evaluation, or automated testing. Each recovery procedure includes the visual symptom, underlying root cause, immediate diagnostic command, exact recovery action, and automated fallback behavior.

---

## Failure Recovery Matrix (12 Scenarios)

### Scenario 1: Total Loss of Internet Connection
* **Symptom**: Terminal displays `ConnectionError`, `MaxRetryError`, or DNS resolution failure during live execution.
* **Root Cause**: Wi-Fi/Ethernet network disconnection preventing HTTPS access to NVIDIA, Groq, or Gemini API hosts.
* **Diagnostic Command**: `ping api.nvidia.com` or `curl -I https://api.groq.com`
* **Recovery Action**: Switch immediately to **Offline Deterministic Fallback Mode**:
  ```powershell
  python code/run_phase15.py
  ```
* **Fallback Behavior**: `router.py` catches network errors, routes messages via fast-path preclassifier and `baseline_policy.py`, applies a -0.15 confidence penalty, and completes batch routing offline in <1.2 seconds.

---

### Scenario 2: Provider Rate Limit Exceeded (HTTP 429)
* **Symptom**: Terminal output displays `HTTP 429 Too Many Requests` or `RateLimitError`.
* **Root Cause**: API call frequency exceeded provider RPM quota limits (NVIDIA 40 RPM, Groq 30 RPM, Gemini 15 RPM).
* **Diagnostic Command**: Inspect `log.txt` for `HTTP 429` status codes.
* **Recovery Action**: Enable automated `QuotaScheduler` throttling or force secondary provider:
  ```powershell
  $env:FORCE_PROVIDER="groq"; python code/run_phase15.py
  ```
* **Fallback Behavior**: `provider.py` catches 429 errors, applies exponential backoff with jitter up to 3 retries, and automatically fails over to the next provider in the chain (NVIDIA -> Groq -> Gemini -> Baseline).

---

### Scenario 3: Provider API Request Timeout or Hang
* **Symptom**: Batch execution pauses indefinitely (>30 seconds) on a single message.
* **Root Cause**: External LLM API endpoint hung or socket connection stalled without sending a response body.
* **Diagnostic Command**: Inspect active process thread status or run with explicit timeout flags.
* **Recovery Action**: Interrupted execution automatically triggers per-request timeout (15s limit in `provider.py`). If manual intervention is needed, press `Ctrl+C` and run:
  ```powershell
  python code/run_phase15.py --use-cache-only
  ```
* **Fallback Behavior**: `provider.py` enforces a strict 15-second request socket timeout, raising `ProviderTimeoutError` and immediately failing over to the secondary provider.

---

### Scenario 4: Missing or Invalid API Keys
* **Symptom**: Terminal logs `AuthenticationError`, `Invalid API Key`, or `401 Unauthorized`.
* **Root Cause**: Environment variables `NVIDIA_API_KEY`, `GROQ_API_KEY`, or `GEMINI_API_KEY` are unset or contain invalid credentials.
* **Diagnostic Command**: `echo $env:NVIDIA_API_KEY` or inspect `.env`.
* **Recovery Action**: Restore environment variables from template or execute in offline mode:
  ```powershell
  copy .env.example .env
  # Or run in offline mode
  python code/run_phase15.py
  ```
* **Fallback Behavior**: `provider.py` checks API key availability on initialization. If keys are missing, it logs a warning and falls back to deterministic preclassification without raising fatal exceptions.

---

### Scenario 5: Image OCR Processing Failure or Missing Image File
* **Symptom**: Log displays `PIL.UnidentifiedImageError` or `FileNotFoundError` for media file in `dataset/media/images/`.
* **Root Cause**: Image file is corrupted, truncated, zero-byte, or path in `images.csv` does not exist on disk.
* **Diagnostic Command**: `python -c "from PIL import Image; Image.open('dataset/media/images/img_008.jpg').verify()"`
* **Recovery Action**: `media_processor.py` catches image loading failures automatically. To force clean media state, clear corrupt entries:
  ```powershell
  python -c "import json; f=open('.cache/media_cache.json','w'); json.dump({},f); f.close()"
  ```
* **Fallback Behavior**: `media_processor.py` sets `ImageAnalysis.failure = True`, `confidence.py` applies a -0.15 media failure penalty, and `unsafe_notify_validator.py` downgrades any proposed `notify` action to `digest`.

---

### Scenario 6: Audio ASR Transcription Failure or Missing Audio File
* **Symptom**: Voice note processing returns empty transcript `""` or throws `AudioDecodeError`.
* **Root Cause**: Audio file in `dataset/media/audio/` is missing, in an unsupported codec, or silent (<0.5s duration).
* **Diagnostic Command**: Test audio file presence and size: `dir dataset\media\audio\`
* **Recovery Action**: Allow automatic fallback to text context analysis:
  ```powershell
  python code/run_phase15.py
  ```
* **Fallback Behavior**: `media_processor.py` catches Whisper ASR decoding errors, returns `VoiceAnalysis.failure = True`, applies a -0.15 confidence penalty, and routes based on sender metadata and message text.

---

### Scenario 7: Missing Python Dependencies or Environment Error
* **Symptom**: Terminal throws `ModuleNotFoundError: No module named 'pydantic'` or `requests`.
* **Root Cause**: Executing Python scripts outside the configured virtual environment or uninstalled packages.
* **Diagnostic Command**: `which python` or `python -c "import pydantic, requests, PIL"`
* **Recovery Action**: Activate the virtual environment or install dependencies from `requirements.txt`:
  ```powershell
  .\venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```
* **Fallback Behavior**: Clean virtual environment ensures zero external library version mismatches.

---

### Scenario 8: Execution from Wrong Working Directory
* **Symptom**: `FileNotFoundError: dataset/messages.csv not found`.
* **Root Cause**: Script invoked from a subdirectory or parent directory instead of project root.
* **Diagnostic Command**: `pwd`
* **Recovery Action**: Navigate to the exact project root directory:
  ```powershell
  cd "c:\Hackathons\Hackerrank\Message Notification Router\hackerrank-orchestrate-august26"
  python code/run_phase15.py
  ```
* **Fallback Behavior**: All scripts in `code/` use relative paths rooted at project root directory via `config.py`.

---

### Scenario 9: Missing Dataset Input Files
* **Symptom**: `FileNotFoundError: dataset/users.csv` or `dataset/messages.csv`.
* **Root Cause**: Required input CSV files in `dataset/` directory were moved or deleted.
* **Diagnostic Command**: `dir dataset\`
* **Recovery Action**: Restore dataset files from source repository or backup archive:
  ```powershell
  git checkout -- dataset/
  ```
* **Fallback Behavior**: Evaluator script `code/evaluate.py` validates presence of all required dataset files before running pipeline.

---

### Scenario 10: Persistent Media Cache Corruption
* **Symptom**: `json.decoder.JSONDecodeError` when reading `.cache/media_cache.json`.
* **Root Cause**: Unexpected power loss or process termination during disk write created malformed JSON in media cache.
* **Diagnostic Command**: `python -c "import json; json.load(open('.cache/media_cache.json'))"`
* **Recovery Action**: Reset the media cache file cleanly:
  ```powershell
  Remove-Item -Force .cache\media_cache.json
  python -c "import os, json; os.makedirs('.cache', exist_ok=True); open('.cache/media_cache.json','w').write('{}')"
  ```
* **Fallback Behavior**: `media_processor.py` catches JSON decode errors on cache load and initializes a new empty cache dictionary automatically.

---

### Scenario 11: Pipeline Checkpoint File Corruption
* **Symptom**: `JSONDecodeError` when reading `outputs/pipeline_checkpoint.json`.
* **Root Cause**: Interrupted batch processing left a partial checkpoint file in `outputs/`.
* **Diagnostic Command**: `python -c "import json; json.load(open('outputs/pipeline_checkpoint.json'))"`
* **Recovery Action**: Delete corrupt checkpoint to restart batch processing cleanly from line 1:
  ```powershell
  Remove-Item -Force outputs\pipeline_checkpoint.json
  python code/run_phase15.py
  ```
* **Fallback Behavior**: Batch runner automatically detects missing or corrupt checkpoint files and executes a clean fresh run.

---

### Scenario 12: Output CSV Schema Validation Failure
* **Symptom**: `evaluate.py` reports `structural_pass: false` or `ValueError: Invalid column header`.
* **Root Cause**: Hand-edited output CSV or corrupted column headers (`message_id,action,message_type...`).
* **Diagnostic Command**: Run structural evaluation audit:
  ```powershell
  python code/evaluate.py --mode structural --input dataset/messages.csv --output outputs/phase15_release_candidate.csv --report evaluation/phase18_val_check.json
  ```
* **Recovery Action**: Regenerate official locked candidate file:
  ```powershell
  python code/run_phase15.py
  copy outputs\phase15_release_candidate.csv output.csv
  ```
* **Fallback Behavior**: `validators.py` enforces canonical column names, UTF-8 encoding without BOM, and strict row count matching (110 rows).
