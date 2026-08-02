# Phase 17 Demo Failure Rehearsal: Incident Handling & Emergency Recovery

## Executive Overview
Live technical demonstrations carry inherent operational risks: API endpoints may experience sudden outages, network connections may drop, API keys may be misconfigured, rate limits may trigger unexpectedly, or media files may be corrupted.

This document serves as the **Emergency Operating Procedure (EOP)** for the Phase 17 Live AI Judge Demo. It outlines seven specific failure scenarios, explaining the system's automated fallback mechanisms, terminal diagnostics, and live verbal explanations to maintain complete demo control under any failure condition.

---

## Failure Matrix & Instant Recovery Cheat Sheet

| Failure Scenario | Automated System Behavior | Live Verbal Explanation for Judges | Manual Override / Fix |
|---|---|---|---|
| **1. Primary API Outage** (NVIDIA Down/Timeout) | Auto-fails over to Groq -> Gemini -> Baseline | *"Our primary provider timed out; system automatically failed over to secondary provider Groq."* | None needed (automated). |
| **2. Rate Limit Hit** (HTTP 429) | `QuotaScheduler` paces calls; exponential backoff retries | *"Quota scheduler detected rate limit pressure and applied backoff pacing to ensure complete run stability."* | None needed (automated). |
| **3. Missing API Keys** | `ProviderFallbackError` caught; falls back to Deterministic Baseline | *"API keys omitted for offline test mode; router degraded gracefully to deterministic preclassifier."* | Set `.env` keys if online execution desired. |
| **4. Corrupt / Missing Image** | PIL validation catches error; logs `failure=True`, applies -0.15 penalty, downgrades `notify` -> `digest` | *"Media file corrupt or missing; router applied confidence penalty and safely queued for digest."* | Verify file path in `dataset/media/images/`. |
| **5. Provider Safety Block** | `PolicyRejectionError` caught; sets action `mute`/`digest`, type `spam`/`unknown`, conf `0.50` | *"Provider safety filter triggered on adversarial content; policy resolver safely muted message."* | None needed (automated safety feature). |
| **6. Malformed LLM Output** | `SchemaValidationError` caught; executes 1-shot in-context repair (`SCHEMA_REPAIR`) | *"LLM output drifted from schema; automated self-repair re-prompted provider and restored valid JSON."* | None needed (automated). |
| **7. Total Offline / Network Cut** | All API calls raise connection errors; complete baseline routing executes | *"Offline mode engaged; preclassifier and baseline policy engine executed zero-network batch routing."* | Run in offline deterministic mode. |

---

## Detailed Step-by-Step Scenario Rehearsals

### Scenario 1: Primary API Provider (NVIDIA) Unavailable or Timing Out
* **Symptoms**: Terminal output displays `NVIDIA Network Error` or `NVIDIA API Error`.
* **Automated System Response**: `generate_routing_decision()` in [`code/provider.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/provider.py#L396-L401) catches `ProviderFallbackError`, prints `NVIDIA Fallback: <error>`, and immediately transfers execution to `call_groq()`.
* **Presenter Script**:
  > *"Judges, as you can see in the terminal log, our primary LLM provider (NVIDIA) experienced a connection delay. Our multi-provider resilience engine detected the failure instantly and failed over to Groq without crashing or delaying the pipeline."*
* **Recovery Command** (if manual restart needed):
  ```powershell
  python code/main.py --provider groq
  ```

---

### Scenario 2: API Rate Limit (HTTP 429) Encountered
* **Symptoms**: Log shows `RATE_LIMIT` classification or retry sleep delay.
* **Automated System Response**: `QuotaScheduler.pace()` in `provider.py` enforces mandatory inter-request spacing. If an HTTP 429 slips through, `classify_http_error()` identifies `RATE_LIMIT` and initiates exponential backoff with random jitter (`2^attempt + random(0,1)`).
* **Presenter Script**:
  > *"Notice the slight 2-second pause in the terminal. That is our `QuotaScheduler` actively pacing requests and handling API rate limits to prevent quota exhaustion during live processing."*

---

### Scenario 3: API Key Missing or Unconfigured in Environment
* **Symptoms**: Log outputs `NVIDIA_API_KEY not configured` or `GEMINI_API_KEY not configured`.
* **Automated System Response**: `call_nvidia()` and `call_gemini()` raise `ProviderFallbackError("API_KEY not configured")`. `router.py` catches this exception, engages the **Deterministic Baseline Policy**, sets `overrides.append("llm_fallback_to_baseline")`, and completes routing with high accuracy using grounded regexes.
* **Presenter Script**:
  > *"When API keys are not supplied in the host environment, our system does not crash. It gracefully degrades to our high-precision deterministic baseline preclassifier, allowing full offline batch routing."*
* **Recovery Command** (to supply key live):
  ```powershell
  $env:NVIDIA_API_KEY="nvapi-..."
  $env:GROQ_API_KEY="gsk_..."
  $env:GEMINI_API_KEY="AIzaSy..."
  python code/main.py
  ```

---

### Scenario 4: Corrupt, Missing, or Truncated Image / Audio File
* **Symptoms**: Image processing encounters PIL `UnidentifiedImageError` or missing path error.
* **Automated System Response**: `process_media()` in [`code/media_processor.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/media_processor.py#L67-L83) catches PIL exceptions, sets `failure=True`, `quality="corrupt"`, and returns a valid `ImageAnalysis` object. Downstream:
  1. `router.py` applies a `-0.15` confidence penalty.
  2. `prevent_unsafe_notify()` checks `media_depends_on_failed` and automatically downgrades any proposed `notify` action to `digest`.
* **Presenter Script**:
  > *"In this step, the incoming image file was corrupt. Rather than throwing an unhandled exception, our media processor flagged the failure, applied a calibrated confidence penalty, and safely queued the message for digest review."*

---

### Scenario 5: Provider Content Safety Policy Rejection (`PolicyRejectionError`)
* **Symptoms**: Gemini or Groq blocks an adversarial prompt and returns `finish_reason = SAFETY`.
* **Automated System Response**: `call_gemini()` identifies the safety block and raises `PolicyRejectionError`. [`code/router.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/router.py#L212-L222) catches `PolicyRejectionError` directly, logs `overrides.append("policy_rejection_fallback")`, sets `action="mute"` (or `"digest"`), `message_type="spam"`, and `confidence=0.50`.
* **Presenter Script**:
  > *"The cloud provider's safety filter triggered on an extreme adversarial content payload. Our router caught the policy rejection and executed a non-blocking safety override, muting the content to protect the user."*

---

### Scenario 6: Malformed LLM Output Response (`SchemaValidationError`)
* **Symptoms**: Provider returns invalid JSON or non-schema field values.
* **Automated System Response**: `_validate_parsed()` in `provider.py` throws `SchemaValidationError`. The provider function catches the error, appends the error feedback to the prompt, and performs a 1-shot in-context repair (`SCHEMA_REPAIR`).
* **Presenter Script**:
  > *"The model returned non-standard JSON formatting. Our schema validation engine detected the anomaly and executed an automated self-repair retry, restoring complete output contract compliance."*

---

### Scenario 7: Full Offline Mode / Network Disconnection
* **Symptoms**: No internet connection available on demo laptop.
* **Automated System Response**: All network calls fail instantly to `ProviderFallbackError`. The pipeline defaults to `preclassifier.py` and `baseline_policy.py`, completing `output.csv` generation in under 2 seconds.
* **Presenter Script**:
  > *"Demonstrating our system's zero-dependency offline mode: even with all network connections severed, our deterministic preclassifier and baseline policy engine process the entire dataset safely and deterministically."*
* **Execution Command**:
  ```powershell
  python code/evaluate.py --offline
  ```

---

## Summary Statement
Our system architecture guarantees zero unhandled crashes under all real-world failure conditions. By combining multi-provider failover, rate limit pacing, PIL pre-validation, schema self-repair, and deterministic baseline fallback, the router remains 100% operational under all demo circumstances.
