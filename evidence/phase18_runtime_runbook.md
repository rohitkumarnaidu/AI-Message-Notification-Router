# Phase 18: Operational Runtime Runbook

## Overview
This runbook provides step-by-step operational instructions for installing, configuring, executing, validating, troubleshooting, and recovering the **HackerRank Orchestrate Message Notification Router**.

---

## 13-Step Operational Runbook

### Step 1: Clone Repository
Clone the project repository to your local workspace:
```bash
git clone https://github.com/hackerrank-orchestrate/message-notification-router.git
cd message-notification-router/hackerrank-orchestrate-august26
```

### Step 2: Create Virtual Environment
Create an isolated Python 3.14 virtual environment:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
Install required runtime and testing packages:
```bash
pip install --upgrade pip
pip install openai google-genai httpx pillow pytest python-dotenv pydantic
```

### Step 4: Configure Environment Variables
Create `.env` in the repository root by copying the template or exporting variables:
```bash
cp .env.example .env
```
Edit `.env` to include valid API keys:
```env
NVIDIA_API_KEY=nvapi-your-key-here
GROQ_API_KEY=gsk_your-key-here
GEMINI_API_KEY=AIzaSy-your-key-here
```

### Step 5: Verify Dataset Placement
Ensure all 12 input CSV files and raw media files exist in `dataset/`:
```bash
ls -la dataset/
```
Verify `messages.csv`, `users.csv`, `groups.csv`, `images.csv`, `voice_notes.csv`, and `dataset/media/` are present.

### Step 6: Run Diagnostic Pre-Check
Execute the system diagnostic check to verify paths, headers, and uniqueness:
```bash
python code/main.py --check
```
*Verification*: Confirm output states `Phase 0 Diagnostic Check Completed Successfully. READY FOR PHASE 1.`

### Step 7: Run Solved Sample Evaluation
Evaluate the pipeline against solved training examples in `dataset/sample_messages.csv`:
```bash
python code/evaluate.py --samples
```
*Verification*: Check accuracy breakdown and metrics summary.

### Step 8: Run Full Candidate Generation
Execute the hybrid production pipeline on `dataset/messages.csv`:
```bash
python code/main.py --run
```
*Verification*: Generates `output.csv` (110 rows) in root directory and archives a copy to `outputs/phase15_release_candidate.csv`.

### Step 9: Validate Output CSV Schema & Integrity
Validate that `output.csv` conforms strictly to the submission contract:
```bash
python -c "from code.loaders import load_csv_records; from code.validators import validate_output_schema; rows = load_csv_records('output.csv'); print(f'Total rows: {len(rows)}'); validate_output_schema(list(rows[0].keys()))"
```
*Verification*: Confirm exactly 110 rows, 6 correct columns (`message_id,action,message_type,reason,confidence,evidence_message_ids`).

### Step 10: Run Unit & Policy Test Suite
Run the full 118-test regression and safety verification suite:
```bash
python -m pytest tests/ -q
```
*Verification*: Confirm `118 passed` with 0 failures.

### Step 11: Inspect Execution Traces & Audit Logs
Review execution logs and cached media analysis:
- Check chat transcript log: `%USERPROFILE%\hackerrank_orchestrate_august26\log.txt` (Windows) or `$HOME/hackerrank_orchestrate_august26/log.txt` (Unix).
- Check media cache: `.cache/media_cache.json`.

### Step 12: Handle Provider Failure & Outage Recovery
If API endpoints become unreachable, experience rate limits (HTTP 429), or run out of quota:
1. The pipeline automatically fails over: NVIDIA -> Groq -> Gemini -> Deterministic Rule Engine.
2. If all APIs fail or keys are revoked, force offline mode:
```bash
# Set environment variable to force local deterministic rules
export FORCE_DETERMINISTIC_FALLBACK=true  # Unix
$env:FORCE_DETERMINISTIC_FALLBACK="true"  # PowerShell
python code/main.py --run
```

### Step 13: Resume Checkpointed Run & Re-Execution
If execution is interrupted mid-run:
1. Media analysis results already processed are safely stored in `.cache/media_cache.json`.
2. Simply re-execute `python code/main.py --run`.
3. Cached media items will load instantaneously without re-calling external APIs.
