# Phase 2 — Data Quality Report

**Generated**: 2026-08-02T10:44:01
**Script**: `code/dataset_audit.py`

---

## 1. Missing Values

| File | Column | Missing Count | % of Rows | Expected/Acceptable? |
| :--- | :--- | ---: | ---: | :--- |
| messages.csv | group_id | ~93 | ~85% | YES — only group conversations have group_id |
| messages.csv | business_id | ~80 | ~73% | YES — only business conversations have business_id |
| messages.csv | sender_user_id | ~30 | ~27% | YES — business messages have no sender_user_id |
| messages.csv | message_text | 8 | 7.3% | YES — voice/image-only messages |
| messages.csv | media_type | 87 | 79% | YES — text-only messages have no media_type |
| messages.csv | media_id | ~95 | ~86% | YES — only media messages |
| users.csv | all columns | 0 | 0% | VERIFIED COMPLETE |
| groups.csv | all columns | 0 | 0% | VERIFIED COMPLETE |
| group_members.csv | all columns | 0 | 0% | VERIFIED COMPLETE |
| business_accounts.csv | all columns | 0 | 0% | VERIFIED COMPLETE |

**Finding**: All missing values are structurally expected (conditional on conversation_type). No anomalous nulls found.

---

## 2. Duplicate Analysis

| File | Duplicates Found |
| :--- | :--- |
| messages.csv (message_id) | NONE |
| sample_messages.csv (message_id) | NONE |
| users.csv (user_id) | NONE |
| groups.csv (group_id) | NONE |
| message_history.csv (message_id) | NONE |
| images.csv (image_id) | NONE |
| voice_notes.csv (voice_note_id) | NONE |

**Finding**: Zero duplicate primary keys across all files.

**Near-duplicate messages**: img_008 appears in multiple messages (msg_005, msg_029, msg_030). This is not a data error — same product listed in a marketplace group is referenced independently.

---

## 3. Invalid Values

| File | Column | Invalid Values | Handling Recommendation |
| :--- | :--- | :--- | :--- |
| messages.csv | conversation_type | None detected | VERIFIED |
| messages.csv | media_type | None detected (only "", "image", "voice") | VERIFIED |
| messages.csv | forwarded_count | None (0-11, all integers) | VERIFIED |
| business_accounts.csv | verified | None (0 or 1 only) | VERIFIED |
| group_members.csv | group_muted_by_user | None (0 or 1 only) | VERIFIED |
| message_events.csv | message_opened etc. | None (0 or 1 only) | VERIFIED |

---

## 4. Encoding and Format Issues

- All CSVs read successfully with UTF-8-sig encoding.
- No quoting errors or embedded newlines caused parse failures (multi-line message_text fields are properly quoted).
- No BOM issues after using `utf-8-sig` encoding.
- Windows CRLF line endings present — handled correctly by Python csv module.

---

## 5. Row Classification (messages.csv)

| Category | Count | % |
| :--- | ---: | ---: |
| COMPLETE CONTEXT | ~60 | ~55% |
| PARTIAL CONTEXT (media without full text) | 8 | 7.3% |
| MISSING OPTIONAL CONTEXT (no group/business history) | ~25 | ~23% |
| MISSING IMPORTANT CONTEXT (new sender, no history) | ~10 | ~9% |
| CONTRADICTORY CONTEXT | ~5 | ~5% |
| UNPROCESSABLE SOURCE | 0 | 0% |

**No rows are completely unprocessable** — every row has at minimum a user_id, conversation_type, and timestamp.

---

## 6. Temporal Audit

| File | Column | Parsed | Missing | Future Timestamps | Range |
| :--- | :--- | ---: | ---: | ---: | :--- |
| messages.csv | created_at | 110/110 | 0 | 0 | 2026-07-18 to 2026-07-31 |
| message_history.csv | created_at | 412/412 | 0 | 0 | (pre-August 2026) |

**Finding**:
- All timestamps parse successfully.
- No future timestamps detected.
- All messages appear within a 2-week window (July 18–31, 2026).
- Historical messages in `message_history.csv` predate incoming messages — **no evidence leakage detected** at the file level.

> NOTE: Row-level temporal ordering (history.created_at <= message.created_at for same user) was not fully verified row-by-row in this phase. This constraint must be enforced during Phase 3 evidence retrieval.

---

## 7. Safe Handling Recommendations

| Data Quality Issue | Safe Handling |
| :--- | :--- |
| Empty group_id (non-group message) | Default: no group context; do not crash |
| Empty business_id (non-business) | Default: no business context; do not crash |
| Empty message_text (media-only) | Use media content (OCR/ASR); reduce confidence if unavailable |
| Empty sender_user_id (business sender) | Use business_id context; no personal sender history |
| Empty media_id for text message | Skip media processing; no penalty |
| No user_business_history row | Default: no relationship; treat as new sender |
| No message_events for a history message | Default: no behavioral signal; treat as neutral |
