# Phase 1 Output Contract Specification

## 1. Deliverable Schema & Format
- **Target Filename**: `output.csv` (written to root or evaluation target directory).
- **Format**: UTF-8 encoded CSV with comma delimiter and CRLF/LF line endings.
- **Required Header (Exact Order)**:
  ```text
  message_id,action,message_type,reason,confidence,evidence_message_ids
  ```
- **Row Count Requirement**: Exactly one output row per incoming row in `dataset/messages.csv`.
- **Row Order Requirement**: Output rows must appear in the exact same sequence as `dataset/messages.csv`.

---

## 2. Allowed Values & Field-Level Contracts

### 2.1 `action` (Final Routing Decision)
Must be exactly one of the following 3 lowercase strings:
- `notify`: Important enough to interrupt user immediately.
- `digest`: Useful, but can be batched and shown later.
- `mute`: Low-value, repetitive, unwanted, suspicious, scam-like, or unsafe.

### 2.2 `message_type` (Best-Fit Message Category)
Must be exactly one of the following 11 lowercase strings:
- `personal`, `urgent`, `event`, `payment`, `business_update`, `promotion`, `greeting`, `forward`, `spam`, `scam`, `unknown`.

### 2.3 `reason` (Human-Readable Explanation)
- **Contract**: Non-empty text string concisely explaining why the routing decision was made for this user.
- **Rule**: Must reflect contextual signals (e.g. sender trust, active group mention, phishing risk).

### 2.4 `confidence` (Calibration Score)
- **Contract**: Floating-point number formatted as a decimal string between `0.0` and `1.0` inclusive (e.g. `0.95`).
- **Rule**: Out-of-bounds numbers (<0.0 or >1.0) or non-numeric strings are rejected by contract validation.

### 2.5 `evidence_message_ids` (Historical Evidence Citation)
- **Contract**:
  - When no useful historical evidence exists: write exactly `none` (lowercase string).
  - When useful historical evidence exists: write one or more historical message IDs separated by semicolons (e.g., `msg_100; msg_102`).
- **Rule**: Referenced IDs should correspond to past messages in `dataset/message_history.csv` and never include incoming `messages.csv` IDs.

---

## 3. Contract Enforcement in Code
The specifications above are programmatically enforced by `code/validators.py` via:
- `validate_output_schema()`
- `validate_row_count_and_ids()`
- `validate_action_values()`
- `validate_message_types()`
- `validate_confidence_range()`
- `validate_reason_not_empty()`
- `validate_evidence_format()`
- `validate_output_records()`
