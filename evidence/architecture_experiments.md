# Architecture Experiments

## Summary
No full codebase implementations were required. Bounded technical experiments were considered, but the measured evidence from Phase 3 (Baseline Error Analysis) provides sufficient deterministic proof of the gaps (e.g., lack of multimodal extraction, lack of semantic urgency parsing) to confidently select the architecture.

## K1 — Structured model-output experiment
* **Status:** Blocked / Deferred to Implementation Phase.
* **Reasoning:** Reliable JSON output is a proven capability of modern LLMs (e.g., Gemini 1.5 Pro/Flash). We will enforce this via strict schema definitions (Pydantic/JSON mode) in Phase 5.

## K2 — Semantic reasoning experiment
* **Status:** Satisfied by Baseline Error Analysis.
* **Reasoning:** `sample_msg_004`, `005`, and `006` explicitly demonstrated that regex rules fail to parse paraphrased urgency. Semantic reasoning is definitively required.

## K4 — OCR or visual experiment
* **Status:** Satisfied by Baseline limitations.
* **Reasoning:** `sample_msg_042` and `046` failed because media fallback defaulted to `digest`. A Vision Language Model (VLM) is definitively required to parse posters and screenshots. 

*No further cost/latency inducing API experiments were run to prevent unauthorized budget consumption prior to Phase 5 approval.*
