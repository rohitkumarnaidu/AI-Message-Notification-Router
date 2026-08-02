# Architecture Decision Record (ADR-001)

**Title:** Selection of Hybrid Deterministic State Machine with Bounded LLM Reasoning
**Status:** Accepted
**Date:** 2026-08-02
**Decision Owner:** Participant / System Owner

## Context
Phase 3 baseline evaluation demonstrated that deterministic regex and rule hierarchies achieve 70% accuracy. The baseline successfully handles safety routing (scams, OTPs) but fails on implied semantic urgency and completely ignores media content (images/voice). The system requires multimodal understanding and nuanced personalization, while guaranteeing strict output schemas and absolute safety.

## Baseline Evidence
- Deterministic safety is highly reliable.
- Rigid regex misses nuanced urgency (false negatives for `notify`).
- Media fallback ignores critical text in images/voice notes.

## Options Considered
- Option A: Deterministic only (Fails semantic/multimodal requirements).
- Option B: Pure LLM prompt (High risk of safety failures and output schema violations).
- Option E: Hybrid Staged Workflow / Explicit state machine (Deterministic Context -> VLM Media Extractor -> Bounded LLM Router -> Deterministic Policy Override).
- Option F: Multi-agent system (Overengineered, high latency, unstable).

## Decision
We will implement **Option E: Hybrid Deterministic State Machine with one Bounded Reasoning Component**.
- **Data Flow:** Input loader → Deterministic context assembler → Media extraction (VLM/ASR) → Deterministic safety features → Historical retrieval → ONE structured LLM call → Deterministic policy resolver → Output validator.

## Why Selected
It is the simplest sufficient architecture that satisfies all Phase 1 requirements. It preserves the perfect output integrity of Option A while incorporating the semantic and multimodal capabilities of Option B/F, without the overengineering risks of Option F.

## Why Alternatives Were Rejected
- **Multi-agent** rejected due to non-deterministic looping, extreme latency, and lack of need (a single LLM prompt can evaluate context if safety overrides are handled deterministically).
- **Pure LLM** rejected because safety overrides (e.g., OTP blocks) must be guaranteed by hardcode, not probabilistic alignment.

## Responsibilities
- **AI Responsibilities:** Extracting text from images/voice, interpreting ambiguous message types, synthesizing personalization from history, generating concise reasons.
- **Deterministic Responsibilities:** File loading, schema validation, safety overrides (OTP, credential theft), confidence clamping, output formatting.

## Tradeoffs, Risks, and Mitigations
- **Tradeoff:** Slower latency than pure deterministic.
- **Risk:** LLM hallucinating evidence IDs. **Mitigation:** Deterministic output validator strips invalid IDs.
- **Risk:** Prompt injection in media. **Mitigation:** Media context marked strictly as untrusted; deterministic policy resolver enforces safety regardless of LLM reasoning.

## Revisit Conditions
Revisit if LLM JSON output failure rate exceeds 1% or if latency exceeds 5 seconds per message.
