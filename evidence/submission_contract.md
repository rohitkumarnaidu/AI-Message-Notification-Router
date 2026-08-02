# Phase 1 Submission Contract Specification

## 1. Required Submission Artifacts
Per `README.md` and `problem_statement.md`, three deliverables must be submitted at hackathon conclusion:

| Artifact | Official Name | Description |
| :--- | :--- | :--- |
| **Code ZIP** | `code.zip` | Full runnable solution, prompts/configs, README, and evaluation scripts. |
| **Predictions CSV** | `output.csv` | Final predictions for all rows in `dataset/messages.csv`. |
| **Chat Transcript** | `chat_transcript` | The development conversation transcript file (`log.txt`). |

---

## 2. ZIP Packaging Rules (`code.zip`)
- **Included Content**:
  - All source modules under `code/`.
  - All automated test suites under `tests/`.
  - Documentation and audit evidence under `evidence/`.
  - Top-level documentation (`README.md`, `problem_statement.md`, `AGENTS.md`, `PHASE_0_SETUP.md`).
  - `.gitignore` and `.env.example`.
- **Strictly Excluded Content**:
  - `dataset/` (including all CSV files and media directories).
  - `.git/` repository history folder.
  - Virtual environments (`.venv/`, `venv/`, `env/`).
  - Python bytecode and cache folders (`__pycache__/`, `.pytest_cache/`, `.hypothesis/`).
  - `.env` files or any file containing real API keys or credentials.
  - Large scratch files or temporary logs.

---

## 3. Transcript Submission Rules (`chat_transcript`)
- **Source Path**: `%USERPROFILE%\hackerrank_orchestrate_august26\log.txt` (Windows).
- **Integrity**: Must contain honest chronological summaries of development turns, commands, and test results.
- **Redaction**: All secret API keys and private credentials must be stripped or redacted as `[REDACTED]`.

---

## 4. Evaluation & Interview Obligations
- **Hidden Test Set**: Submitted `output.csv` is evaluated against hidden ground-truth labels.
- **AI Judge / Interview Readiness**: System design, architecture choices, prompt strategies, and evaluation methodology must be documented and explainable during post-submission evaluation.
