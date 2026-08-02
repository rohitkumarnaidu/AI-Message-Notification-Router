# Phase 1 Failure-Behavior Specification

## 1. Core Principles
- **No Unsupported Labels**: Official submission schema only allows `notify`, `digest`, or `mute`. Never emit an unsupported label like `error`, `abstain`, or `review`.
- **Confidence Reduction**: When upstream components (OCR, ASR, retrieval, or LLM) fail or degrade, lower `confidence` (e.g. to `0.30`–`0.50`) to signal uncertainty while outputting a conservative routing decision.
- **Safety Priority**: Any unresolvable scam, phishing, or safety risk defaults to `mute` with `message_type` `scam` or `spam`.

---

## 2. Failure Category Matrix

### 2.1 Input Failures
| Failure ID | Trigger | Detection | Retry Allowed? | Fallback Behavior | Output Action | Confidence Effect | Log Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| FAIL-IN-01 | Missing optional context (e.g. group/business FK) | Null/empty string in CSV | No | Process with available user/message features | Context-dependent | Reduce by 0.10 | Log warning with `message_id` |
| FAIL-IN-02 | Unrecognized timestamp or encoding | Exception during parsing | No | Fall back to default string parsing | Context-dependent | Reduce by 0.15 | Log warning with `message_id` |

### 2.2 Media Failures (OCR / ASR)
| Failure ID | Trigger | Detection | Retry Allowed? | Fallback Behavior | Output Action | Confidence Effect | Log Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| FAIL-MED-01 | Media file missing or corrupt | FileNotFoundError / IOError | No | Use `message_text` or sender context; note media missing | `digest` (or `mute` if suspicious) | Reduce to `0.40` | Log error with media path |
| FAIL-MED-02 | Low OCR/ASR transcription confidence | Provider confidence score < threshold | Yes (1x) | Use partial transcript + sender/user context | Conservative `digest` | Reduce by 0.20 | Log warning |

### 2.3 Retrieval Failures
| Failure ID | Trigger | Detection | Retry Allowed? | Fallback Behavior | Output Action | Confidence Effect | Log Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| FAIL-RET-01 | Zero historical evidence found | Search returns empty list | No | Output `none` for `evidence_message_ids` | Context-dependent | No penalty if truly new sender | Debug log |
| FAIL-RET-02 | Conflicting or weak history | Multiple contradictory past actions | No | Prioritize most recent reaction event | Conservative `digest` | Reduce by 0.10 | Debug log |

### 2.4 Model Failures (LLM / VLM / API)
| Failure ID | Trigger | Detection | Retry Allowed? | Fallback Behavior | Output Action | Confidence Effect | Log Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| FAIL-MOD-01 | API timeout or rate limit | HTTP 429 / TimeoutException | Yes (3x with backoff) | Rule-based baseline fallback classifier | Conservative rule prediction | Set to `0.35` | Log warning / retry count |
| FAIL-MOD-02 | Invalid JSON or schema violation | JSONDecodeError / Schema mismatch | Yes (1x prompt retry) | Fallback to deterministic rule classifier | Conservative rule prediction | Set to `0.35` | Log schema error |
| FAIL-MOD-03 | Hallucinated evidence ID | ID not in `message_history.csv` | Caught by validation filter | Strip invalid ID; replace with `none` if empty | Keep action | Reduce by 0.15 | Log hallucinated ID |

### 2.5 Safety Failures (Scams / Phishing / Injection)
| Failure ID | Trigger | Detection | Retry Allowed? | Fallback Behavior | Output Action | Confidence Effect | Log Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| FAIL-SAF-01 | Prompt injection attempt in text | Keyword/pattern heuristic | No | Block injection; treat sender as untrusted | `mute` (`scam`/`spam`) | Set to `0.99` | Log security alert |
| FAIL-SAF-02 | Credential/payment pressure from unknown sender | Phishing/scam pattern match | No | Immediately mute and flag as scam | `mute` (`scam`) | Set to `0.99` | Log safety event |

### 2.6 Output Failures
| Failure ID | Trigger | Detection | Retry Allowed? | Fallback Behavior | Output Action | Confidence Effect | Log Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| FAIL-OUT-01 | Row count or order mismatch | Caught by `validators.py` | N/A (Fatal pipeline error) | Abort CSV write; report diagnostic trace | N/A | N/A | Log critical error |
| FAIL-OUT-02 | Invalid field value (e.g. out-of-range float) | Caught by `validators.py` | N/A (Fatal pipeline error) | Abort CSV write; report diagnostic trace | N/A | N/A | Log critical error |
