# Phase 18 Known Limitations & Future Work Analysis

## Executive Overview
In accordance with production AI engineering standards, this document provides an **honest, transparent audit of the 10 known system limitations** in the **Message Notification Router**. For each limitation, it documents the impact description, affected component, current mitigation implemented, grounded evidence, planned future improvements, and release blocking assessment.

---

## Limitations Audit Matrix

### 1. Small Solved Benchmark Sample Size (30 Messages)
* **Impact Description**: Ground-truth label evaluation in `dataset/sample_messages.csv` contains only 30 solved messages, limiting statistical coverage across all combinations of 11 message types and 3 actions.
* **Affected Component**: Benchmarking harness (`code/evaluate.py --mode solved`).
* **Current Mitigation**: Expanded test coverage using an automated 118-unit-test regression suite (`tests/`) covering edge-case combinations.
* **Grounded Evidence**: [`evaluation/phase15_solved_report.json`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/evaluation/phase15_solved_report.json) (`sample_count: 30`).
* **Future Improvement**: Synthesize a 1,000-message expert-labeled benchmark dataset.
* **Release Blocking Assessment**: **NON-BLOCKING** (Full 110 dataset verified via `unlabeled-audit` mode).

---

### 2. Limited Solved Multimodal Samples (Image & Voice Notes)
* **Impact Description**: Solved sample messages contain only 3 voice notes and 5 image messages, providing a narrow evaluation window for multimodal ground truth.
* **Affected Component**: Multimodal evaluation harness (`code/evaluate.py --mode media-subset`).
* **Current Mitigation**: Created synthetic isolated audio and image test suites (`tests/test_media_processor.py`) to verify OCR and ASR threat detection independently.
* **Grounded Evidence**: [`reports/phase11_voice_with_audio_report.json`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/reports/phase11_voice_with_audio_report.json).
* **Future Improvement**: Expand multimodal evaluation dataset to include 200 diverse image posters and multi-speaker voice notes.
* **Release Blocking Assessment**: **NON-BLOCKING** (Image OCR and Voice ASR fully verified on synthetic test suites).

---

### 3. External Provider API & Quota Dependency for Live Escalation
* **Impact Description**: Escalating complex messages to LLMs requires live network access and valid API keys (`NVIDIA_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`).
* **Affected Component**: Provider client module (`code/provider.py`).
* **Current Mitigation**: Built `QuotaScheduler` delays, exponential backoff, 4-tier provider failover, and a zero-dependency offline deterministic runner (`code/run_phase15.py`).
* **Grounded Evidence**: [`evidence/phase17_provider_resilience.md`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/evidence/phase17_provider_resilience.md).
* **Future Improvement**: Fine-tune a small local SLM (e.g. Llama-3-8B) for zero-latency offline escalation.
* **Release Blocking Assessment**: **NON-BLOCKING** (Offline runner handles complete dataset cleanly in <1.2s).

---

### 4. Model Output Variability Across Provider Endpoints
* **Impact Description**: Different LLM provider endpoints (NVIDIA Llama-3.1 vs Groq Llama-3.3 vs Gemini 2.5) may output slight variations in reasoning phrasing for ambiguous messages.
* **Affected Component**: LLM proposal generation (`code/provider.py`).
* **Current Mitigation**: Enforced rigid JSON output schemas and subordinate policy resolver guardrails (`code/safety_policy.py`) to ensure deterministic final actions regardless of model phrasing variance.
* **Grounded Evidence**: [`evidence/phase14_schema_reliability.md`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/evidence/phase14_schema_reliability.md).
* **Future Improvement**: Standardize temperature setting to 0.0 and enforce JSON mode constraints across all endpoints.
* **Release Blocking Assessment**: **NON-BLOCKING** (Policy resolver enforces action consistency across all provider outputs).

---

### 5. Phonetic ASR Transcription Variability on Hinglish Audio
* **Impact Description**: Background noise or accent variations in Hinglish voice notes can cause Whisper ASR to misspell key words (e.g. transcribing "OTP" as "o tee pee" or "pay karo" as "pekaro").
* **Affected Component**: Voice ASR processor (`code/media_processor.py`, `code/multilingual_safety.py`).
* **Current Mitigation**: Implemented phonetic normalization rules in `multilingual_safety.py` (`oh tee pee` -> `OTP`, `pay karo` -> `pay_karo`).
* **Grounded Evidence**: [`code/multilingual_safety.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/multilingual_safety.py#L40-L90).
* **Future Improvement**: Integrate a fine-tuned IndicWhisper model for native South Asian language speech recognition.
* **Release Blocking Assessment**: **NON-BLOCKING** (Phonetic normalizer catches common ASR misspellings).

---

### 6. Low-Resolution OCR Text Extraction Uncertainty
* **Impact Description**: Highly compressed or low-resolution image posters (e.g. low-quality JPEG flyers) can cause partial text extraction in OCR.
* **Affected Component**: Image media processor (`code/media_processor.py`).
* **Current Mitigation**: Combined OCR text extraction with Gemini 2.5 Flash visual summarization (`visual_summary`), allowing visual threat elements (financial logos, QR codes) to be detected even if OCR text is partial.
* **Grounded Evidence**: [`evidence/phase10_visual_analysis.md`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/evidence/phase10_visual_analysis.md).
* **Future Improvement**: Add image pre-processing super-resolution and contrast enhancement filters prior to OCR.
* **Release Blocking Assessment**: **NON-BLOCKING** (Visual summarization supplements OCR text extraction).

---

### 7. Ambiguous Relative Time Phrase Parsing ("Later Today", "Soon")
* **Impact Description**: Relative temporal phrases lacking concrete time markers (e.g. "let's meet later today", "update coming soon") cannot be resolved to precise timestamps.
* **Affected Component**: Temporal context extractor (`code/temporal.py`).
* **Current Mitigation**: `temporal.py` classifies relative phrases as `urgency_language_only=True` and `concrete_deadline=False`. Non-concrete urgency is conservatively prevented from interrupting quiet hours.
* **Grounded Evidence**: [`evidence/phase13_temporal.md`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/evidence/phase13_temporal.md).
* **Future Improvement**: Implement conversational thread tracking to resolve relative time references against preceding message context.
* **Release Blocking Assessment**: **NON-BLOCKING** (Conservative quiet hours downgrade prevents improper interruptions).

---

### 8. Sparse Historical Interaction Logs for New/Inactive Users
* **Impact Description**: New or inactive users in `users.csv` have sparse message history in `message_history.csv`, providing limited behavioral reply/dismiss signals.
* **Affected Component**: Context aggregator & evidence selector (`code/context_builder.py`, `code/evidence_selector.py`).
* **Current Mitigation**: When historical interaction count is zero, `evidence_selector.py` safely outputs `evidence_message_ids = ["none"]` and `preclassifier.py` relies on grounded message text signals.
* **Grounded Evidence**: [`evidence/phase15_evidence_audit.md`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/evidence/phase15_evidence_audit.md).
* **Future Improvement**: Implement cold-start default profiles based on user category preferences.
* **Release Blocking Assessment**: **NON-BLOCKING** (System safely outputs `["none"]` for sparse history).

---

### 9. Default Quiet Hours Window Fallback for Incomplete User Profiles
* **Impact Description**: User profiles in `users.csv` that do not specify explicit quiet hours windows default to a standard system window (UTC 22:00-07:00).
* **Affected Component**: Notification load & quiet hours evaluator (`code/quiet_load.py`).
* **Current Mitigation**: Default quiet hours window (22:00-07:00) applies conservative action downgrades for unconfigured users, protecting them from late-night interruptions.
* **Grounded Evidence**: [`code/quiet_load.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/quiet_load.py#L15-L35).
* **Future Improvement**: Automatically infer user sleep schedules from historical message timestamp activity.
* **Release Blocking Assessment**: **NON-BLOCKING** (Conservative fallback protects users by default).

---

### 10. Limited Historical Evidence Grounding Labels in Dataset
* **Impact Description**: The dataset provides sample message outputs but does not provide exhaustive ground-truth evidence ID labels for all 110 messages.
* **Affected Component**: Evidence selector evaluation (`code/evidence_selector.py`).
* **Current Mitigation**: Enforced strict deterministic relevance scoring (+3 sender, +2 group, +1 type, +1-2 token overlap) and programmatic allowlist verification to guarantee 100% evidence validity.
* **Grounded Evidence**: [`evidence/phase15_evidence_threshold.md`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/evidence/phase15_evidence_threshold.md).
* **Future Improvement**: Annotate complete multi-label evidence relationships across all historical messages.
* **Release Blocking Assessment**: **NON-BLOCKING** (Deterministic allowlisting prevents false or invalid evidence IDs).
