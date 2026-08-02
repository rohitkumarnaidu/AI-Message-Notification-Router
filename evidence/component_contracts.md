# Component Contracts

## 1. Input Loader & Schema Validator
* **Purpose:** Read CSVs, ensure row completeness, preserve order.
* **Inputs:** raw `.csv` files.
* **Outputs:** `List[dict]` representing incoming messages and context.
* **Failure:** Malformed row raises validation exception (fatal).

## 2. Context Assembler
* **Purpose:** Build typed `IncomingMessageContext` combining relationships, metadata, and deterministic risk signals.
* **Inputs:** raw message dict, global context tables.
* **Outputs:** `IncomingMessageContext` object.
* **Failure:** Missing context issues non-fatal warning, marks `missing_context=True`.

## 3. Media Processor (LLM/ASR)
* **Purpose:** Extract transcripts and OCR summaries from multimodal data.
* **Inputs:** `media_id`, `media_type`.
* **Outputs:** `MediaAnalysis` object.
* **Failure:** Missing file or API timeout returns empty transcript with `failure=True`. Does not crash row.

## 4. Evidence Retriever
* **Purpose:** Find relevant historical interactions.
* **Inputs:** `IncomingMessageContext`.
* **Outputs:** `List[EvidenceCandidate]`.
* **Failure:** Misses return empty list.

## 5. Structured LLM Router
* **Purpose:** Semantic reasoning and intent classification.
* **Inputs:** Prompt string containing JSON context.
* **Outputs:** `RouterDecision` (action, type, reason).
* **Failure:** JSON parse error or timeout triggers 1 retry, then fallback to Deterministic routing.

## 6. Policy Resolver
* **Purpose:** Enforce safety and resolve conflicts between LLM and hardcoded rules.
* **Inputs:** `RouterDecision`, `IncomingMessageContext`.
* **Outputs:** `FinalDecision`.
* **Failure:** Fatal if unable to resolve.

## 7. Output Writer & Final Validator
* **Purpose:** Format output and verify integrity against input IDs.
* **Inputs:** `List[FinalDecision]`.
* **Outputs:** `output.csv`.
* **Failure:** Validation mismatch fails process to prevent corrupt submission.
