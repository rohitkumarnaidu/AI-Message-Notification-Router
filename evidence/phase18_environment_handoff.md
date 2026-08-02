# Phase 18: Environment & Infrastructure Handoff Specification

## 1. Runtime Environment & OS Compatibility
- **Primary Tested Operating System**: Windows 11 Home / Pro (x64)
- **Supported OS Platforms**: Windows 10/11, macOS 12+ (Apple Silicon & Intel), Linux (Ubuntu 22.04+ LTS)
- **Python Version**: `Python 3.14.6` (Compatible with Python 3.10+)
- **Virtual Environment Tooling**: `venv` / `virtualenv` / `uv`
- **Package Manager**: `pip >= 24.0`

---

## 2. Required System Tools
- **Git**: Version 2.40+ (Required for source code management and commit verification)
- **Shell Options**: PowerShell 7+, Windows Command Prompt (`cmd.exe`), or Bash
- **System Memory**: Minimum 4 GB RAM (8 GB recommended for parallel test execution)
- **Disk Space**: 500 MB free disk space for dataset, virtual environment, and cached media assets

---

## 3. Encoding & File System Standards
- **File Encoding**: UTF-8 (Strict, without BOM)
- **Line Endings**: Unix `\n` or Windows `\r\n` supported; output files generated using standard `\n`
- **Path Separation**: Handled natively using Python `pathlib.Path` cross-platform abstractions
- **Case Sensitivity**: Explicit lower-case checking for dataset columns, action strings, and message types

---

## 4. Network Requirements & Provider Endpoints

### Outbound Network Access (Live Execution Mode)
When running with active LLM providers, outbound HTTPS (Port 443) access is required to the following endpoints:

| Provider | Service / Purpose | Target Host Endpoint | Base URL |
|---|---|---|---|
| **NVIDIA API** | Primary Text Routing (Llama-3.1-70B) | `integrate.api.nvidia.com` | `https://integrate.api.nvidia.com/v1` |
| **Groq API** | Secondary Text (Llama-3.3-70B) & ASR (Whisper) | `api.groq.com` | `https://api.groq.com/openai/v1` |
| **Google Gemini API** | Image OCR / Visual Analysis & Fallback Text | `generativelanguage.googleapis.com` | Google GenAI SDK Default |

### Offline / Deterministic Mode
When `FORCE_DETERMINISTIC_FALLBACK=true` or when no API keys are configured:
- **Network Access**: Zero outbound network requests required.
- **Data Safety**: All processing executes 100% locally using `preclassifier.py` and rule-based safety engines.

---

## 5. Environment Variable Reference

```env
# Primary API Credentials
NVIDIA_API_KEY=nvapi-your-nvidia-api-key-here
GROQ_API_KEY=gsk_your-groq-api-key-here
GEMINI_API_KEY=AIzaSy-your-gemini-api-key-here

# Provider Configuration Overrides
MODEL_PROVIDER=gemini
MODEL_NAME=gemini-3.5-flash
IMAGE_PROVIDER=gemini
ASR_PROVIDER=groq

# Fallback & Rate Limiting Controls
FORCE_DETERMINISTIC_FALLBACK=false
MAX_RETRIES=1
MAX_CALLS_PER_MESSAGE=2
TIMEOUT_SECONDS=30
MAX_REQUESTS_PER_MINUTE=10
MIN_SECONDS_BETWEEN_CALLS=7.0
```

---

## 6. Rate Limiting & Quota Management

To operate reliably under API rate limits (especially free tier quotas), the provider engine implements explicit `QuotaScheduler` pacing:

| Provider Endpoint | API Quota Limit | Pacing Spacing (`min_spacing`) | Failure & Retry Strategy |
|---|---|---|---|
| **NVIDIA API** | ~40 RPM Tier | `2.5 seconds` | 3 attempts, exponential backoff with jitter |
| **Groq API** | ~30 RPM Tier | `2.0 seconds` | 3 attempts, exponential backoff with jitter |
| **Google Gemini API** | ~15 RPM Tier | `4.0 seconds` | 3 attempts, exponential backoff with jitter |

### Circuit Breakers & Timeout Rules
- **Connect Timeout**: 5.0 seconds
- **Read Timeout**: 15.0 seconds
- **Max Retries per Provider**: 3
- **Policy Rejection Catch**: Immediatly fails over without redundant re-prompting if provider safety block is triggered.
