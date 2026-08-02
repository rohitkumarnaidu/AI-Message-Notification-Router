# Phase 17 Provider Resilience: Multi-Provider Failover & Rate Limit Defense

## Executive Overview
Production AI applications that rely on external Cloud API providers (NVIDIA, Groq, Google Gemini) face unavoidable real-world challenges: HTTP 429 rate limiting, network timeouts, API quota exhaustion, temporary server outages (HTTP 5xx), schema formatting drifts, and provider safety policy rejections.

To guarantee **100% uptime** and **zero batch run failures** across all rows in `dataset/messages.csv`, our system incorporates a multi-tiered **Provider Resilience Infrastructure** ([`code/provider.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/provider.py)).

---

## 1. Multi-Provider Fallback Architecture

```
                       [Routing Decision Request]
                                   |
                                   v
                  +---------------------------------+
                  | Primary: NVIDIA API             |
                  | (meta/llama-3.1-70b-instruct)   |
                  +---------------------------------+
                                   |
                     (Provider Error / Quota Exhaustion)
                                   |
                                   v
                  +---------------------------------+
                  | Secondary: Groq API             |
                  | (llama-3.3-70b-versatile)       |
                  +---------------------------------+
                                   |
                     (Provider Error / Quota Exhaustion)
                                   |
                                   v
                  +---------------------------------+
                  | Tertiary: Google Gemini API     |
                  | (gemini-2.5-flash)              |
                  +---------------------------------+
                                   |
                     (Provider Error / Quota Exhaustion)
                                   |
                                   v
                  +---------------------------------+
                  | Fallback: Deterministic Baseline|
                  | (baseline_policy.py)            |
                  +---------------------------------+
```

### Fallback Execution Logic
The entry point function `generate_routing_decision()` in [`code/provider.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/provider.py#L393-L409) executes the fallback sequence:
1. Calls `call_nvidia()`. If successful, returns structured decision.
2. If `ProviderFallbackError` is caught (rate limit, connection error, server crash), logs warning and immediately falls back to `call_groq()`.
3. If Groq fails with `ProviderFallbackError`, falls back to `call_gemini()`.
4. If all API providers fail, [`code/router.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/router.py#L224-L231) catches `ProviderFallbackError` and executes a **Deterministic Baseline Fallback**, setting `action` from baseline rules, logging `overrides.append("llm_fallback_to_baseline")`, and applying a `-0.10` confidence penalty.

---

## 2. Quota Schedulers & Proactive Rate Limit Pacing

Rather than waiting for HTTP 429 Rate Limit errors and retrying with backoff, our system implements proactive **Rate Limit Pacing** via `QuotaScheduler`:

```python
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
```

### Configured Provider Spacing
* **NVIDIA Scheduler**: `QuotaScheduler(2.5)` (Enforces 2.5-second spacing between requests, keeping calls safely under NVIDIA's 40 RPM limit).
* **Groq Scheduler**: `QuotaScheduler(2.0)` (Enforces 2.0-second spacing, keeping calls under Groq's 30 RPM limit).
* **Gemini Scheduler**: `QuotaScheduler(4.0)` (Enforces 4.0-second spacing, keeping calls under Gemini's 15 RPM limit).

---

## 3. Fine-Grained HTTP Error Classification

[`code/provider.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/provider.py#L82-L100) categorizes all network and API exceptions into explicit error buckets using `classify_http_error()`:

| HTTP Code / Exception Pattern | Error Category | System Response |
|---|---|---|
| `HTTP 429` | `RATE_LIMIT` | Retry with exponential backoff + jitter; fallback if exhausted. |
| `HTTP 401 / 403` | `AUTHENTICATION` | Immediate failover to next provider (no retry). |
| `HTTP 404` | `MODEL_NOT_FOUND` | Immediate failover to next provider. |
| `HTTP 400` + "policy"/"safety" | `PROVIDER_POLICY_REJECTION` | Raises `PolicyRejectionError`; triggers safe mute/digest override. |
| `HTTP 5xx` | `SERVER_ERROR` | Exponential backoff retry (up to 3 attempts), then failover. |
| Timeout / Connection / EOF | `TRANSIENT_NETWORK` | Retries with exponential backoff (`2^attempt + jitter`). |

---

## 4. Policy Rejection Handling (`PolicyRejectionError`)

When a prompt contains adversarial text or extreme content, cloud providers (especially Gemini) may refuse to process the request and return a content policy block (`finish_reason = SAFETY / BLOCKLIST / PROHIBITED_CONTENT`).

Treating a policy rejection as an unhandled crash or retrying the same blocked prompt endlessly is a failure mode. Instead:
1. `call_gemini()`, `call_nvidia()`, or `call_groq()` catch the provider policy block and raise `PolicyRejectionError`.
2. [`code/router.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/router.py#L212-L222) catches `PolicyRejectionError` directly.
3. Automatically applies a **Safety Policy Rejection Fallback**:
   * Action set to `mute` (if media present) or `digest`.
   * Message type set to `spam` or `unknown`.
   * Reason set to: *"Content flagged by provider safety policies; safely routed to prevent exposure."*
   * Confidence set to `0.50`.
   * Appends `"policy_rejection_fallback"` to execution trace.

---

## 5. Schema Validation & Dynamic Self-Repair

LLMs occasionally return JSON that violates the strict output contract (e.g., invalid `action` string, non-numeric `confidence`, invalid `evidence_message_ids`).

Our system enforces strict schema validation via `_validate_parsed()`:
* **Allowed Actions Check**: Validates `action in {"notify", "digest", "mute"}`.
* **Allowed Types Check**: Validates `message_type in ALLOWED_TYPES` (defaults to `"unknown"` if invalid).
* **Confidence Range Check**: Coerces confidence to float and validates `0.0 <= conf <= 1.0`.
* **Evidence Allowlist Verification**: Filters `evidence_message_ids` against the pre-approved candidate allowlist. Unrecognized IDs are stripped to prevent evidence hallucination.

### Dynamic Self-Repair Flow
If `json.loads()` or `_validate_parsed()` fails (`SchemaValidationError`):
1. Captures the exact validation error message.
2. Appends the broken response and error feedback to the conversation context:
   `"PREVIOUS OUTPUT ERROR: {e}. Return ONLY valid JSON."`
3. Retries the provider call once with feedback (`SCHEMA_REPAIR` mode).
4. If self-repair fails a second time, raises `ProviderFallbackError` to trigger provider failover.

---

## 6. Multimodal Resumable Caching Engine (`code/media_processor.py`)

Media processing (OCR and ASR) is compute-intensive and network-bound. `media_processor.py` implements a persistent, resumable disk cache at `.cache/media_cache.json`:

* **MD5 Content Verification**: Computes MD5 hash of raw image or audio files to detect content changes.
* **Prompt Versioning**: Cache keys include processor version (`p11v1`). Updating prompt logic invalidates older cache entries cleanly.
* **Resumability**: If a processing run is interrupted, re-running the script reuses existing cached entries instantaneously, resuming exactly where it left off without duplicating API calls or exceeding daily quotas.

---

## Summary Statement
Through proactive rate limit pacing, multi-provider fallback chains, graceful policy rejection handling, schema self-repair, and resumable disk caching, our system guarantees unbroken operational resilience under all network and API conditions.
