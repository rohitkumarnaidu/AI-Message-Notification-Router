# Failure and Fallback Matrix

| Component | Failure | Detection | Retry | Fallback | Confidence Effect | Output Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Media Processor** | OCR/VLM Timeout or Missing File | Try/Catch, API Error | 1 | `failure=True` empty transcript | Reduces confidence | Text-only routing |
| **Evidence Retriever** | Missing History | Empty List | 0 | Return `[]` | No direct effect | Standard context processing |
| **LLM Router** | Model Timeout / 503 | API Error | 1 | Deterministic Baseline Policy | N/A | Fully deterministic baseline reason |
| **LLM Router** | Invalid JSON Schema | Pydantic parse error | 1 | Deterministic Baseline Policy | N/A | Fully deterministic baseline reason |
| **LLM Router** | Prompt Injection / Scam | Deterministic Safety Check | 0 | Policy Resolver forces `mute` | Forces `1.0` | Output reflects security override |
| **Output Validator** | Corrupt IDs / Row count mismatch | Final validation check | 0 | Fatal Exception | N/A | Process crashes (prevents corrupt CSV) |

Core Rule: **Never convert a technical failure into a confident normal answer.** All media/LLM failures gracefully degrade to the proven 70%-accurate Deterministic Baseline from Phase 3.
