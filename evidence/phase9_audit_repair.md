# Phase 9 Audit & Repair: Historical Retrieval Hardening

## Overview
Phase 9 focused on securing the historical retrieval pipeline (`code/retriever.py`) against cross-user leakage, future-data leakage, and prediction-ID leakage, while implementing rigorous evidence scoring and thresholding.

## 1. Retrieval Hardening Implementations
The following rules were strictly implemented and validated through unit tests (`tests/test_retrieval.py`):
- **User Isolation:** All historical evidence strictly matches the receiving `user_id`. (Rule 15)
- **Temporal Eligibility:** No evidence message where `created_at >= msg.timestamp` is returned. (Rule 16)
- **Relationship Scoring:** Prioritizes matching sender, business, or group. (Rule 17)
- **Score Thresholding:** Minimum score threshold of 3 required for evidence inclusion. (Rule 18, 19)
- **Fallback to "none":** If no valid historical evidence is found, `evidence_message_ids` correctly defaults to `["none"]`. (Rule 19)
- **Reason Consistency:** The `router.py` automatically corrects the `reason` string to avoid false claims of historical evidence if `["none"]` was retrieved. (Rule 21)

## 2. Evaluation Results
The sample pipeline (`outputs/phase8_sample_candidate.csv`) was evaluated against the solved sample dataset.
- **Action Accuracy:** 0.6333
- **Action Macro F1:** 0.5635
- **Type Accuracy:** 0.2333 (Improved)
- **Type Macro F1:** 0.2972 (Improved)

*Observation:* Resolving the evidence retrieval flaws allowed the LLM router to slightly improve message type precision.

## 3. Full Candidate Pipeline Execution
The `parallel_pipeline.py` successfully processed all 110 messages across the three providers (Gemini, Groq, NVIDIA) with appropriate fallback behavior during rate limits (429 errors). The full output has been correctly saved to `outputs/phase8_parallel_candidate.csv` maintaining 100% output schema integrity without breaking the environment.

## 4. Leakage and Hygiene Verification
- **Cross-user Leakage:** Zero instances of cross-user leakage were found in the final outputs.
- **Git Tracking:** Validated that `.cache/` and generated outputs are appropriately untracked (except `outputs/.gitkeep`).

Phase 9 is complete. The historical retrieval architecture is hardened, tested, and fully aligned with the requirements.
