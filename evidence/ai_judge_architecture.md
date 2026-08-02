# AI Judge Architecture & End-to-End Flow

Pipeline Stages:
1. Context Assembly & User Isolation
2. Sender/Group/Business Relationship Builder
3. Eligible Historical Evidence Filtering
4. Multimodal Processing (Image OCR & Visual Summaries)
5. Voice Note ASR & Hinglish Normalization
6. Deterministic Safety & Risk Detectors
7. Interruption Policy (Temporal Urgency, Quiet Hours, Load)
8. Group Mute Policy & Direct Mention Resolver
9. Selective Preclassifier (Fast-Path 55.4%)
10. Multi-Provider Resilient LLM Chain (NVIDIA -> Groq -> Gemini)
11. Pydantic Proposal Validation & Self-Repair
12. Evidence Allowlist & Grounded Reason Builder
13. Confidence Calibration Clamping [0.85, 0.99]
14. Unsafe-Notify Validator & CSV Output Formatting

Failure Path & Resilience:
- Rate limits or API outages switch provider via QuotaScheduler.
- Complete network failure falls back to Deterministic Baseline Policy with -0.15 confidence penalty.
