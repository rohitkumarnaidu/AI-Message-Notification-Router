# Phase 18: Output Contract & Submission Deliverable Specification

## 1. Executive Summary
This document specifies the exact structural, value, ordering, formatting, and validation rules for the submission deliverable file `output.csv`. Any deviation from these rules will cause automated grading failure.

---

## 2. Header & Column Specification
The file `output.csv` MUST contain exactly 6 columns in the exact order shown below:

```csv
message_id,action,message_type,reason,confidence,evidence_message_ids
```

| Column Index | Field Name | Data Type | Constraint & Allowed Values | Description |
|---|---|---|---|---|
| 1 | `message_id` | String | Must match input `messages.csv` exactly | Unique identifier of incoming message (e.g. `msg_0001`) |
| 2 | `action` | Enum String | `notify` \| `digest` \| `mute` | Target routing action |
| 3 | `message_type` | Enum String | One of 11 allowed categories (see §3.2) | Semantic classification of content |
| 4 | `reason` | String | Non-empty string, no internal code/raw JSON | Concise, grounded human-readable explanation |
| 5 | `confidence` | Float | Floating point number in range `[0.0, 1.0]` | Calibrated confidence score (never `1.00`) |
| 6 | `evidence_message_ids` | String | Semicolon-separated list or `none` | Historical evidence message IDs (e.g. `message_0012;message_0045` or `none`) |

---

## 3. Value Constraints & Allowed Taxonomies

### 3.1 Allowed Actions (`action`)
Must be exactly one of the following 3 strings (case-sensitive, lower-case):
- `notify`: Immediate user interruption required.
- `digest`: Non-urgent message batched for later review.
- `mute`: Unwanted, repetitive, promotional, spam, or high-risk scam message suppressed.

### 3.2 Allowed Message Types (`message_type`)
Must be exactly one of the following 11 strings (case-sensitive, lower-case):
1. `personal`: Personal conversation from known/trusted contact.
2. `urgent`: Time-critical request requiring immediate user response.
3. `event`: Scheduled meeting, appointment, webinar, or event.
4. `payment`: Legitimate financial transaction, bill, EMI, or statement.
5. `business_update`: Operational status update from a business (shipping, tracking, order update).
6. `promotion`: Marketing, sale, discount, or promotional offer.
7. `greeting`: Harmless conversational greeting (hi, hello, good morning).
8. `forward`: Chain message or frequently forwarded broadcast content.
9. `spam`: Unsolicited marketing or low-value broadcast content.
10. `scam`: High-risk credential phishing, financial fraud, OTP theft, or impersonation.
11. `unknown`: Unclassified message lacking actionable signals.

### 3.3 Confidence Score (`confidence`)
- **Type**: Numeric float formatted as decimal (e.g., `0.92`, `0.85`).
- **Allowed Range**: `0.0 <= confidence <= 1.0`.
- **Calibration Rule**: Max confidence ceiling is `0.99`. Automatic assignment of `1.0` is strictly forbidden by `confidence.py`.

### 3.4 Evidence Message IDs (`evidence_message_ids`)
- **Separator**: Multiple historical evidence IDs MUST be separated by a semicolon `;` (e.g. `message_0001;message_0005`).
- **None Behavior**: When no historical evidence applies, the field MUST contain the string `"none"`.
- **Exclusion Rules**: The incoming message ID (e.g. `msg_0001`), event IDs, duplicate IDs, or future timestamps are strictly forbidden in evidence.

---

## 4. Row Count & ID Ordering Rules
- **Row Count**: Exactly **110 prediction rows** matching the 110 incoming message records in `dataset/messages.csv`.
- **Row Ordering**: Rows in `output.csv` MUST follow the exact sequence of `message_id`s in `dataset/messages.csv`.
- **ID Completeness**: Every `message_id` present in `dataset/messages.csv` MUST appear exactly once in `output.csv`. No missing IDs, no extra IDs, no duplicates.

---

## 5. File Encoding & Clean Export Rules
- **Encoding**: UTF-8 without byte order mark (BOM).
- **Line Ending**: Unix `\n` or Windows `\r\n`.
- **Index Column**: MUST NOT include any row index column (e.g., no leading `0,1,2...`).
- **Trace/Debug Columns**: MUST NOT include internal trace columns, override logs, or debug metadata (`execution_mode`, `safety_signals`, `policy_override`).
- **Delimiter**: Standard comma `,`. Standard double quotes `"` applied only if text contains commas.
