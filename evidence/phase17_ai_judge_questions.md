# Phase 17 AI Judge Questions & Concise Evidence-Backed Answers

This document contains **26 technical AI Judge questions** covering all operational, architectural, safety, and resilience aspects of the HackerRank Orchestrate Message Notification Router. Every answer is grounded directly in the implementation files of `code/`.

---

## Section 1: Architecture & Pipeline Design

### Q1: What is the high-level architecture of your message notification router?
**Answer**: Our system uses a **14-Stage Selective Hybrid Architecture**. Deterministic pre-classifiers ([`code/preclassifier.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/preclassifier.py)) and safety detectors ([`code/safety_detectors.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/safety_detectors.py)) handle high-certainty messages (scams, greetings, clear events) on a fast-path (<1ms). Complex or ambiguous messages are escalated to a multi-provider LLM chain (NVIDIA Llama-3.1-70B -> Groq Llama-3.3-70B -> Gemini 2.5 Flash in [`code/provider.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/provider.py)). All decisions pass through a 10-level Priority Policy Resolver and an Unsafe-Notify Prevention Validator before output generation.

### Q2: Why did you choose a hybrid approach instead of relying 100% on an LLM?
**Answer**: Relying 100% on an LLM creates severe latency (1-3s per message), high API costs, vulnerability to prompt injection, potential provider rate limiting, and output drift. Our hybrid approach routes ~60% of clear messages via fast-path deterministic rules (0 API cost, <1ms latency) while reserving LLM intelligence for ambiguous, multi-signal contexts.

### Q3: How do you prevent system execution crashes when external LLM providers fail?
**Answer**: Through a multi-tiered fallback architecture in [`code/provider.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/provider.py) and [`code/router.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/router.py). If NVIDIA fails or hits rate limits, execution falls back to Groq; if Groq fails, it falls back to Gemini. If all providers fail, the router catches `ProviderFallbackError` and executes a deterministic baseline fallback (`baseline_policy.py`) with a -0.10 confidence penalty.

### Q4: How is data flow organized between stages?
**Answer**: Data flow uses frozen dataclass contracts defined in [`code/schemas.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/schemas.py). `IncomingMessageContext` collects metadata and media analysis; `RouterInput` standardizes data for the preclassifier; `SafetySignals` tracks safety provenance; `RouterProposal` holds candidate actions; `PolicyDecision` applies overrides; and `FinalDecision` produces the final `output.csv` row.

---

## Section 2: Personalization & User Context

### Q5: How does your system ensure the same message produces different actions for different users?
**Answer**: By evaluating message content against six user-specific context axes: quiet hours window, current notification load, group mute state, business opt-in/opt-out status, trusted sender hierarchy, and historical reply/dismiss/report ratios ([`code/context_builder.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/context_builder.py)).

### Q6: How are quiet hours and notification load handled?
**Answer**: In [`code/quiet_load.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/quiet_load.py), quiet hours downgrade standard `notify` actions to `digest`, unless overridden by verified **genuine urgency** (e.g., concrete immediate deadline). High notification load (`daily_notifications > 50`) downgrades non-urgent notifications to `digest`, while preserving direct mentions and direct messages.

### Q7: How does group policy interact with user mute settings?
**Answer**: In [`code/group_policy.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/group_policy.py), if a user has muted a group (`is_group_muted=True`), routine broadcast messages route to `mute`. Upgrades to `notify` occur *only* if the message is a direct `@user` mention sent by a recognized **Group Admin**. Standard direct mentions route to `digest`.

---

## Section 3: Multimodal Media Processing

### Q8: How are image messages processed and evaluated for safety?
**Answer**: [`code/media_processor.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/media_processor.py) pre-validates images via PIL, hashes binary bytes (MD5), checks `.cache/media_cache.json`, and invokes Gemini multimodal structured analysis (`provider.analyze_image()`). It extracts OCR text, visual summary, QR code presence, financial logos, promotional banners, and visual prompt injection.

### Q9: How are voice notes transcribed and analyzed across languages?
**Answer**: [`code/media_processor.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/media_processor.py#L98-L160) uses Groq Whisper (`whisper-large-v3-turbo`) with Gemini fallback. Transcripts pass through [`code/multilingual_safety.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/multilingual_safety.py) for ASR phonetic correction (`oh tee pee` -> `OTP`) and Hinglish pattern matching (`turant pay karo`, `apna otp batao`) to detect spoken OTP theft, payment pressure, and urgency.

### Q10: What happens when an image or audio file is missing or corrupted?
**Answer**: `media_processor.py` catches PIL verification errors or missing file paths, returns a structured analysis with `failure=True`, and logs the error. [`code/confidence.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/confidence.py#L24) applies a mandatory -0.15 confidence penalty, and [`code/unsafe_notify_validator.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/unsafe_notify_validator.py#L123) downgrades any proposed `notify` action to `digest`.

---

## Section 4: Safety, Scams & Prompt Injection

### Q11: How do you differentiate credential requests from legitimate security warnings?
**Answer**: In [`code/safety_detectors.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/safety_detectors.py#L208-L246), `detect_credential_risk()` evaluates request patterns (`share your OTP`, `send password`) vs. warning patterns (`never share your OTP`, `do not give PIN`). Credential requests set `credential_request=True` (triggering `mute`/`scam`), while warnings set `credential_warning=True` and are safely allowed.

### Q12: How do you defend against prompt injection attacks embedded in message text or images?
**Answer**: [`code/safety_detectors.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/safety_detectors.py#L435-L496) scans text and OCR for override commands (`set action=notify`, `ignore previous instructions`, `system prompt`). When detected, `prompt_injection_signal` is set to `True`. [`code/safety_policy.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/safety_policy.py) Level 1 policy immediately forces `action="mute"` and `message_type="scam"`, bypassing LLM reasoning.

### Q13: What is the Unsafe-Notify Prevention Validator?
**Answer**: [`code/unsafe_notify_validator.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/unsafe_notify_validator.py) is a final 10-point check before output CSV generation. It blocks any `notify` action proposed for credential risks, prompt injection, scam/spam types, suspicious payment pressure, fake urgency, promo-only content, or failed media.

### Q14: How do you ensure zero unsafe notifications in output.csv?
**Answer**: `audit_final_output()` in `unsafe_notify_validator.py` inspects every row in `output.csv`. If any `notify` action exists for `scam` or `spam`, or violates safety constraints, `unsafe_notify_remaining` is incremented. The system enforces `unsafe_notify_remaining == 0` as a non-negotiable release blocker.

---

## Section 5: Provider Resilience & Rate Limits

### Q15: How do you handle API rate limits (HTTP 429) across providers?
**Answer**: Proactively using `QuotaScheduler` in [`code/provider.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/provider.py#L55-L76), which enforces mandatory request spacing: 2.5s for NVIDIA (40 RPM), 2.0s for Groq (30 RPM), and 4.0s for Gemini (15 RPM). Reactively, HTTP 429 triggers exponential backoff with random jitter up to 3 retries before failing over to the next provider.

### Q16: How do you handle provider content safety rejections (PolicyRejectionError)?
**Answer**: When a provider rejects a prompt (`SAFETY`/`BLOCKLIST`), `provider.py` raises `PolicyRejectionError`. [`code/router.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/router.py#L212) catches this error and applies a safe fallback: setting action to `mute` (if media present) or `digest`, type to `spam`/`unknown`, confidence to `0.50`, and logging `policy_rejection_fallback`.

### Q17: How does schema self-repair work when an LLM returns malformed JSON?
**Answer**: `_validate_parsed()` in [`code/provider.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/provider.py#L103-L139) validates JSON structure against schema contracts. If validation fails (`SchemaValidationError`), the system appends the exact error message to the prompt and retries the provider call once (`SCHEMA_REPAIR` mode).

### Q18: What is your media caching strategy?
**Answer**: [`code/media_processor.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/media_processor.py#L18-L38) computes MD5 hashes of raw media files and maintains a persistent disk cache at `.cache/media_cache.json`. Submitting identical files yields instantaneous cache hits, avoiding duplicate API calls and enabling execution resumability.

---

## Section 6: Evidence Selection & Retrieval

### Q19: How do you select historical evidence message IDs?
**Answer**: [`code/evidence_selector.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/evidence_selector.py) evaluates candidate messages for the same user from `message_history.csv`. Candidates are scored based on sender/business match (+3), group match (+2), conversation type (+1), historical events (+1 to +3 for report/mute/dismiss), and non-stopword token overlap (+1 to +2). The top 3 candidates are selected.

### Q20: How do you prevent evidence hallucination and cross-user data leakage?
**Answer**: `evidence_selector.py` enforces strict filtering: `history_user_id == incoming_user_id`, strict temporal ordering (`history_created_at < incoming_created_at`), and exclusion of incoming message IDs and event IDs. Programmatically, `_validate_parsed()` in `provider.py` strips any ID returned by an LLM that is not present in the pre-approved candidate allowlist.

### Q21: When does the system output evidence_message_ids = ["none"]?
**Answer**: When no historical candidate for the user scores above zero, when the incoming message has no prior interaction history, or when evidence validation fails. `["none"]` is explicitly formatted per schema requirements.

---

## Section 7: Confidence Calibration & Schema Integrity

### Q22: How is confidence calibrated across different routing paths?
**Answer**: [`code/confidence.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/confidence.py) computes confidence using base certainty and explicit penalties: -0.15 for provider fallback, -0.10 for schema repair, -0.10 for signal conflict, and -0.15 for media failure. Final confidence is clamped to `[0.30, 0.99]`.

### Q23: Why does your system explicitly disallow a confidence score of 1.00?
**Answer**: `calibrate_confidence()` enforces `if final_conf >= 1.0: final_conf = 0.99`. Automatic 1.00 confidence implies zero-risk omniscience, which is uncalibrated in real-world stream processing with potential missing context.

### Q24: How do you ensure reasons are grounded and non-generic?
**Answer**: [`code/reason_builder.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/reason_builder.py) builds human-readable explanations (<200 chars) by combining triggered rule templates with dynamic feature flags (e.g., suspicious link detection, media unavailability, missing context). `router.py` also runs evidence-consistency corrections to prevent reasons from claiming historical evidence when `evidence_message_ids = ["none"]`.

---

## Section 8: Evaluation, Tradeoffs & Failure Recovery

### Q25: What are the main engineering tradeoffs in your system design?
**Answer**: 
1. *Selective Hybrid vs. Pure LLM*: Sacrifices LLM processing on simple messages for 60% lower cost and <1ms latency.
2. *Deterministic Safety vs. LLM Autonomy*: Overrides LLM decisions with deterministic policy to guarantee zero unsafe notifications.
3. *Strict Allowlisting vs. Vector RAG*: Restricts evidence candidates to prevent hallucination and future timestamp leakage.

### Q26: How do you verify system readiness before submission?
**Answer**: By running `python code/evaluate.py` against solved sample messages, auditing `output.csv` format via `audit_final_output()`, verifying column schemas, confirming `unsafe_notify_remaining == 0`, and building clean submission packages via `build_phase16_submission.py`.

---

## Summary Statement
These 26 questions and answers provide comprehensive, code-grounded evidence demonstrating that our Message Notification Router is architected for maximum safety, resilience, personalization, and evaluation rigor.
