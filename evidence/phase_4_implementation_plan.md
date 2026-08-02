# Phase 4 Implementation Plan (For Phase 5)

This sequence will be executed in Phase 5 to realize the selected Hybrid Architecture.

## 1. Finalize Typed Schemas (Pydantic)
* **Goal:** Create strict models for `IncomingMessageContext`, `RouterDecision`, `FinalDecision`.
* **Dependency:** None.

## 2. Build Media Processing
* **Goal:** Implement VLM call for images and ASR/VLM for voice notes. Add caching based on `media_id`.
* **Dependency:** Typed Schemas, API Keys.

## 3. Build Evidence Retrieval
* **Goal:** Implement deterministic candidate generation and ranking.
* **Dependency:** Context tables.

## 4. Build Structured Router (LLM)
* **Goal:** Write the prompt, inject context, and configure the LLM for JSON structured output.
* **Dependency:** Typed Schemas, Media Processing, Evidence Retrieval.

## 5. Build Policy Resolver
* **Goal:** Implement the deterministic safety and override gates.
* **Dependency:** Structured Router output.

## 6. Build Confidence Calibrator & Final Validator
* **Goal:** Apply deterministic confidence adjustments. Plug into the existing `validate_row_count_and_ids`.
* **Dependency:** Policy Resolver.

## 7. Run Evaluation & Regression
* **Goal:** Run `evaluate.py` against the `sample_messages.csv` to ensure performance exceeds the 70% Baseline. Ensure all baseline tests (`test_baseline.py`) pass.
