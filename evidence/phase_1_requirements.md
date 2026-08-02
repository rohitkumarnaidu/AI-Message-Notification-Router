# Phase 1 Official Requirements & Challenge Registers

## 1. Requirement Extraction

### F1 — Functional Requirements
- **F1.1**: Must read incoming messages from `dataset/messages.csv`. [Source: README.md, problem_statement.md]
- **F1.2**: Must read context from 11 supplementary CSVs in `dataset/` (`users.csv`, `groups.csv`, `group_members.csv`, `business_accounts.csv`, `user_business_history.csv`, `message_history.csv`, `message_events.csv`, `images.csv`, `voice_notes.csv`, `daily_notification_summary.csv`, `sample_messages.csv`).
- **F1.3**: Must inspect local image files and voice-note media files under `dataset/media/` referenced by `images.csv` and `voice_notes.csv`.
- **F1.4**: Must produce one prediction row in `output.csv` for every `message_id` in `dataset/messages.csv`.
- **F1.5**: Must output exactly 6 columns in order: `message_id,action,message_type,reason,confidence,evidence_message_ids`.
- **F1.6**: Must be runnable from the terminal.
- **F1.7**: Must not use organizer-only files or hardcoded challenge prediction labels.

### F2 — Non-Functional Requirements
- **F2.1**: Multimodal Reasoning: System must reason over text, image posters/screenshots, and voice notes.
- **F2.2**: Personalization: Routing decisions must reflect individual user notification behavior, quiet hours, group roles, and business relationships.
- **F2.3**: Safety & Risk Protection: Clear scams, phishing, or safety risks must be routed to `mute` with `message_type` `scam` or `spam` regardless of engagement.
- **F2.4**: Reproducibility: All random seeds, prompts, and configurations must be documented in code.
- **F2.5**: Secret Hygiene: API keys and credentials must be read from environment variables; zero hardcoding.

### F3 — Submission Requirements
- **F3.1**: `code.zip`: Full runnable solution, prompts/configs, README, and evaluation files (excluding datasets, venvs, and Git folders).
- **F3.2**: `output.csv`: Complete predictions matching `messages.csv` rows 1-to-1.
- **F3.3**: `chat_transcript`: External log file (`%USERPROFILE%\hackerrank_orchestrate_august26\log.txt`) documenting development.

### F4 — Evaluation Requirements
- **F4.1**: Evaluated against hidden ground-truth labels by HackerRank / AI Judge.
- **F4.2**: Scoring dimensions: correctness of `action`, correctness of `message_type`, usefulness and consistency of `reason`, relevance of `evidence_message_ids`, and calibration of `confidence`.

---

## 2. Challenge Registers

### Confirmed Facts Register
| Fact ID | Official Text / Quote | Source File | Interpretation / Implication |
| :--- | :--- | :--- | :--- |
| FACT-01 | "For every row in dataset/messages.csv, produce one row in output.csv" | README.md §What You Need to Build | 1-to-1 row parity required between input messages and output CSV. |
| FACT-02 | "Required columns, in order: message_id, action, message_type, reason, confidence, evidence_message_ids" | problem_statement.md §Required output | Schema header and order are strictly immutable. |
| FACT-03 | "action: notify, digest, mute" | problem_statement.md §Allowed values | Only these 3 lowercase action strings are permitted. |
| FACT-04 | "message_type: personal, urgent, event, payment, business_update, promotion, greeting, forward, spam, scam, unknown" | problem_statement.md §Allowed values | Only these 11 lowercase message types are permitted. |
| FACT-05 | "write none if no useful historical message exists" | problem_statement.md §Output meaning | Case-sensitive string `none` required when evidence is absent. |
| FACT-06 | "semicolon-separated historical message IDs used as evidence" | problem_statement.md §Output meaning | Multiple evidence IDs must be separated by `;`. |
| FACT-07 | "For image and voice-note messages, images.csv and voice_notes.csv only provide file paths; your system should inspect the media files themselves." | README.md §What You Need to Build | Must process multimodal media files in `dataset/media/`. |

### Assumptions Register
| Assumption ID | Assumption | Why Necessary | Supporting Evidence | Risk if Wrong | Resolution Method | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| ASSUMP-01 | `confidence` must be formatted as a decimal string between `0.0` and `1.0` | Output schema requires numeric confidence | standard ML calibration | Rejected by submission parser | Tested in `validators.py` | CONFIRMED |
| ASSUMP-02 | `evidence_message_ids` must reference historical IDs from `message_history.csv` | Evidence must explain historical context | problem_statement.md §8 | Evidence penalized if pointing to future/incoming IDs | Verified in validation rules | ACTIVE |

### Unknowns Register
| Unknown ID | Question | Why It Matters | Safest Temporary Behavior | How to Resolve | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| UNK-01 | Are there missing optional fields in `messages.csv` (e.g. `group_id` for personal chats)? | Parser could fail on None/empty values | Treat empty CSV strings as optional nulls | Inspect schema in Phase 1 | RESOLVED |
| UNK-02 | What is the exact evaluation weight between action correctness vs. reason consistency? | Affects model prompt tuning | Optimize all 5 evaluation dimensions equally | Refer to official scoring guidelines | DEFERRED TO PHASE 2 |

### Contradictions Register
| Contradiction ID | First Statement | Second Statement | Source Locations | Safest Interpretation | Decision Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| CONTRA-01 | None identified in official docs | N/A | README.md vs problem_statement.md | Both documents agree on 6 columns, 3 actions, 11 message types, and transcript rules. | VERIFIED CLEAN |
