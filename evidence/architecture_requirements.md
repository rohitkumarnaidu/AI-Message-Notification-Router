# Architecture Requirements

| Requirement ID | Observed baseline failure | Frequency | Severity | Affected samples | Current workaround | Capability required | Complexity justified? | Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| REQ-01 | Semantic reasoning for paraphrased urgency | High (3/9 errors) | High (misses notifications) | sample_msg_004, 005, 006 | Strict Regex triggers | LLM-based intent recognition | YES | Deterministic fails on "this week" vs "in 5 minutes". |
| REQ-02 | Better personalization synthesis | Medium (2/9 errors) | Medium | sample_msg_044, 019 | Hardcoded opt-in/opt-out gates | LLM balancing conflicting signals | YES | Baseline overrides legitimate updates if past behavior is slightly negative. |
| REQ-03 | Visual understanding (OCR/VLM) | Medium | High | sample_msg_042, 046, 048 | Fallback to "digest" | Multimodal vision model | YES | Posters and screenshots with embedded promotions/deadlines are completely missed. |
| REQ-04 | Deterministic safety overrides | High | Critical | N/A (tested positively in baseline) | Hardcoded precedence | Rule-based safety gate AFTER LLM reasoning | YES | ML models can be jailbroken; safety must remain deterministic. |
| REQ-05 | Structured output enforcement | N/A | High | N/A | Print validation | Strict JSON schema mode (e.g. Gemini JSON mode) | YES | Need machine-readable outputs for downstream routing. |
| REQ-06 | Historical evidence retrieval | High | Medium | N/A (Baseline limits to 3) | Hardcoded relationship matching | Semantic/Behavioral retrieval | YES | Hard limit loses context if user has rich interaction history. |
