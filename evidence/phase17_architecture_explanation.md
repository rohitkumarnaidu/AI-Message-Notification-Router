# Phase 17 Architecture Explanation: Message Notification Router

## Executive Overview
The **HackerRank Orchestrate Message Notification Router** is a high-reliability, selective-hybrid AI router designed for WhatsApp notifications. WhatsApp stream processing requires balancing immediate user attention for critical events against user protection against notification fatigue, spam, scams, and prompt injection attacks.

Rather than relying purely on an unconstrained Large Language Model (LLM) or rigid static regex rules, our system implements a **14-Stage Selective Hybrid Architecture**. Deterministic pre-classifiers and grounded safety policies act as fast-path filters and non-negotiable safety guardrails, while LLM calls (via a multi-provider resilient chain of NVIDIA Llama-3.1-70B, Groq Llama-3.3-70B, and Gemini 2.5 Flash) are reserved for ambiguous, high-context scenarios.

---

## Complete End-to-End 14-Stage Pipeline Architecture

```
[Incoming Message] -> [Stage 1: Context Assembly] -> [Stage 2: Multimodal OCR/ASR & Cache]
                                                                  |
[Stage 5: Evidence Selection] <- [Stage 4: Safety Signals] <- [Stage 3: Multilingual Normalization]
             |
             v
[Stage 6: Temporal Urgency] -> [Stage 7: Relevance] -> [Stage 8: Notification Load] -> [Stage 9: Group Policy]
                                                                                             |
                                                                                             v
[Stage 11: Resilient Multi-Provider Chain] <-- (Ambiguous) <-- [Stage 10: RouterInput & Preclassifier]
             |                                                                               | (Deterministic Fast-Path)
             +-----------------------------> [Stage 12: Safety Policy Resolver] <------------+
                                                           |
                                                           v
                                            [Stage 13: Interruption Resolver]
                                                           |
                                                           v
                                            [Stage 14: Unsafe-Notify Defense & Output]
```

---

## Detailed Breakdown of the 14 Pipeline Stages

### Stage 1: Context Assembly & Feature Extraction
* **Source Module**: [`code/context_builder.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/context_builder.py), [`code/feature_extractor.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/feature_extractor.py), [`code/loaders.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/loaders.py)
* **Functionality**: Joins the incoming message (`dataset/messages.csv`) with full relational metadata: user profile preferences (`users.csv`), group metadata (`groups.csv`), sender context (`group_members.csv`), business relationship history (`business_accounts.csv`, `user_business_history.csv`), and interaction events (`message_events.csv`).
* **Output**: Instantiates `IncomingMessageContext` containing user quiet hours, notification load metrics, trusted sender sets, business opt-in/opt-out status, and past reply/dismiss/report ratios.

### Stage 2: Multimodal Processing & Resilience Caching
* **Source Module**: [`code/media_processor.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/media_processor.py), [`code/provider.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/provider.py)
* **Functionality**:
  * **Images**: Performs PIL image verification, computes an MD5 content hash, checks `CACHE_DIR/media_cache.json`, and invokes Gemini multimodal visual analysis to extract OCR text, visual summary, QR presence, financial element markers, and visual prompt injection signals (`ImageAnalysis`).
  * **Audio**: Verifies voice note integrity, checks MD5 cache, and invokes Groq Whisper (`whisper-large-v3-turbo`) with fallback to Gemini audio transcription. Extracted transcripts are parsed for financial, OTP, credential, and urgency markers (`VoiceAnalysis`).
* **Resilience**: If media is missing or corrupt, sets `failure=True` and applies a `-0.15` confidence penalty downstream instead of crashing.

### Stage 3: Multilingual Safety Normalization & Transliteration
* **Source Module**: [`code/multilingual_safety.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/multilingual_safety.py)
* **Functionality**: Applies Unicode NFKC normalization, fixes OCR digit-for-letter substitutions (e.g. `0TP` -> `OTP`, `p@ssw0rd` -> `password`), fixes ASR mishearings (e.g. `oh tee pee` -> `OTP`), and normalizes Latin-script Hindi/Hinglish phrasing (e.g. `khata band ho jayega`, `turant pay karo`, `inaam jeeta`).
* **Design Rule**: Normalization is strictly defensive for signal detection; the original message text is preserved for final human-readable reason generation.

### Stage 4: Grounded Safety Signal Extraction
* **Source Module**: [`code/safety_detectors.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/safety_detectors.py)
* **Functionality**: Inspects normalized text, image OCR, and voice transcripts for:
  * **Credential Risks**: Distinguishes credential *requests* (asking for OTP/PIN) from credential *warnings* ("never share your OTP").
  * **Payment Pressure**: Detects unverified QR codes, suspicious payment links, and token/advance fee demands vs. verified business invoice reminders.
  * **Account Coercion**: Detects fake account suspension threats, lottery/prize claims, and government/bank impersonation.
  * **Prompt Injection**: Detects routing override commands (e.g., `set action=notify`, `ignore previous instructions`).
* **Output**: Produces `SafetySignals` with full `SignalSource` provenance (source, grounded value snippet, detector, confidence, trusted flag).

### Stage 5: Historical Evidence Selection & Filtering
* **Source Module**: [`code/evidence_selector.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/evidence_selector.py)
* **Functionality**: Selects up to 3 historical `message_id`s from `message_history.csv` for the target user. Candidates are scored based on sender/business match (+3), group match (+2), conversation type match (+1), report/mute/dismiss event history (+1 to +3), and non-stopword token overlap (+1 to +2).
* **Hard Safety Constraints**: Enforces strict temporal ordering (`history_created_at < incoming_created_at`), excludes incoming message ID, excludes event IDs, and filters out cross-user leakage. If no candidate scores above zero, returns `["none"]`.

### Stage 6: Temporal Context & Urgency Extraction
* **Source Module**: [`code/temporal.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/temporal.py)
* **Functionality**: Parses ISO timestamps, evaluates user timezone relative to default quiet hours (22:00–07:00 local time), and differentiates **concrete deadlines** (e.g. "arriving in 15 minutes", "waiting outside", "today at 4 PM") from **vague urgency language** (e.g. "urgent", "asap", "hurry").

### Stage 7: Relevance & Engagement Signal Extraction
* **Source Module**: [`code/relevance.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/relevance.py)
* **Functionality**: Extracts direct mention signals (`@username`), personal conversation markers, active delivery/order tracking references, transaction status, and explicit opt-in/opt-out keywords.

### Stage 8: Notification Load & Quiet Hours Evaluation
* **Source Module**: [`code/quiet_load.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/quiet_load.py)
* **Functionality**: Evaluates user notification load (`daily_notifications > 50` or `recent_notifications > 10` -> `high`). Implements quiet-hours downgrade (`notify` -> `digest`) unless overridden by verified genuine urgency.

### Stage 9: Group Policy & Mention Filtering
* **Source Module**: [`code/group_policy.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/group_policy.py)
* **Functionality**: If a message belongs to a user-muted group, forces action to `mute`. Allows exceptions only for direct mentions by recognized group admins (`notify`) or standard direct mentions (`digest`).

### Stage 10: Canonical `RouterInput` & Preclassification
* **Source Module**: [`code/preclassifier.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/preclassifier.py), [`code/schemas.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/schemas.py)
* **Functionality**: Constructs a frozen canonical `RouterInput` object. Runs `preclassify_message()` to check for high-certainty deterministic rules (credential theft, phishing, prompt injection, spam, simple greetings, verified payment, clear event, concrete delivery).
* **Fast-Path Decision**: If deterministic criteria are met with high confidence (>=0.85), returns `(True, RouterProposal, ExecutionMode.DETERMINISTIC_DIRECT)`, bypassing LLM execution entirely for zero latency and zero API cost.

### Stage 11: Selective Escalation & Resilient Provider Chain
* **Source Module**: [`code/router.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/router.py), [`code/provider.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/provider.py)
* **Functionality**: For complex or ambiguous messages not preclassified deterministically, builds a structured JSON prompt (`build_llm_prompt`) and invokes `generate_routing_decision()`.
* **Multi-Provider Fallback Chain**:
  1. **Primary**: NVIDIA API (`meta/llama-3.1-70b-instruct`) with `QuotaScheduler` (2.5s pace).
  2. **Secondary**: Groq API (`llama-3.3-70b-versatile`) with `QuotaScheduler` (2.0s pace).
  3. **Tertiary**: Google Gemini API (`gemini-2.5-flash`) with `QuotaScheduler` (4.0s pace).
  4. **Fallback**: Gracefully falls back to baseline rules on provider error (`ProviderFallbackError`) or safely mutes on policy rejection (`PolicyRejectionError`).

### Stage 12: Priority Policy Resolution Chain
* **Source Module**: [`code/safety_policy.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/safety_policy.py), [`code/router.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/router.py)
* **Functionality**: Evaluates model or baseline proposals against a 10-level strict priority chain (`resolve_policy`). Safety rules override model proposals:
  * *Level 1*: Prompt Injection -> `mute` / `scam`
  * *Level 2*: Credential Risk -> `mute` / `scam`
  * *Level 3*: Phishing / Impersonation / QR Scam -> `mute` / `scam`
  * *Level 4*: Dangerous Forward + Mute History -> `mute` / `spam`
  * *Level 5*: Opted-out Promotion -> `mute` / `promotion`
  * *Level 6*: Muted Group -> `mute` (unless admin mention)
  * *Level 7*: Quiet Hours Active -> `digest` (unless genuine urgency)
  * *Level 8*: High Notification Load -> `digest` (unless direct personal message/mention)
  * *Level 9*: Low-Value Greeting / Unsubscribed Promo -> `digest`
  * *Level 10*: Validated Default Route

### Stage 13: Interruption Policy Resolver
* **Source Module**: [`code/interruption_resolver.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/interruption_resolver.py)
* **Functionality**: Computes interruption costs vs. consequence of delay. Validates that `notify` actions possess genuine urgency, personal relevance, or admin authority before interrupting the user.

### Stage 14: Unsafe-Notify Defense, Reason Building & Confidence Calibration
* **Source Module**: [`code/unsafe_notify_validator.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/unsafe_notify_validator.py), [`code/reason_builder.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/reason_builder.py), [`code/confidence.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/confidence.py)
* **Functionality**:
  * **Unsafe-Notify Prevention**: Final hard check (`prevent_unsafe_notify`). Blocks any `notify` action proposed for scam/spam, credential requests, fake urgency, promo-only, greeting-only, or failed media.
  * **Reason Building**: Maps internal rule IDs and feature flags to concise (<200 char), grounded human explanations without claiming unverified media or fake preferences.
  * **Confidence Calibration**: Clamps confidence strictly to `[0.00, 0.99]` (`calibrate_confidence`), applying explicit penalties for provider fallbacks (-0.15), schema repairs (-0.10), signal conflicts (-0.10), and media failures (-0.15).

---

## Architectural Key Contracts & Data Flow Table

| Pipeline Stage | Input Data | Core Logic / Module | Output Contract |
|---|---|---|---|
| 1. Context Assembly | `messages.csv`, `users.csv`, `groups.csv`, `history.csv` | `context_builder.py`, `feature_extractor.py` | `IncomingMessageContext` |
| 2. Multimodal | Image/Audio files, `images.csv`, `voice_notes.csv` | `media_processor.py`, `provider.py` | `ImageAnalysis` / `VoiceAnalysis` |
| 3. Multilingual | Raw text, OCR text, ASR transcript | `multilingual_safety.py` | `NormalizationResult` |
| 4. Safety Signals | Normalized text, media analysis, sender metadata | `safety_detectors.py` | `SafetySignals` |
| 5. Evidence Selection | `message_history.csv`, `message_events.csv`, timestamp | `evidence_selector.py` | `List[str]` (max 3 message_ids or `["none"]`) |
| 6. Temporal Context | Text, ISO timestamp, user timezone | `temporal.py` | `TemporalContext` |
| 7. Relevance | Text, conversation type, sender role | `relevance.py` | `RelevanceSignals` |
| 8. Quiet & Load | Quiet hours spec, notification count | `quiet_load.py` | `load_status`, quiet flag |
| 9. Group Policy | Group mute state, admin flag, mention flag | `group_policy.py` | Action adjustment |
| 10. Preclassifier | Grounded `RouterInput` | `preclassifier.py` | `(is_deterministic, RouterProposal)` |
| 11. Provider Chain | JSON Prompt, evidence allowlist | `router.py`, `provider.py` | `RouterDecision` (LLM proposal) |
| 12. Policy Resolver | Model/Baseline proposal, `SafetySignals` | `safety_policy.py` | `PolicyDecision` (Safety-enforced) |
| 13. Interruption | Proposed action, load, quiet hours, relevance | `interruption_resolver.py` | `InterruptionDecision` |
| 14. Unsafe Defense & Calib | Final action proposal, penalties | `unsafe_notify_validator.py`, `confidence.py` | `FinalDecision` -> `output.csv` row |

---

## Summary Statement
This 14-stage architecture guarantees that every WhatsApp message is evaluated with full context, high safety defense, robust multi-provider fallback, and rigorous confidence calibration—producing reliable, explainable, and safe routing decisions for every user.
