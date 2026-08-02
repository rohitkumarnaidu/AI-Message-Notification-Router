# Phase 2 — Schema Audit Report

**Generated**: 2026-08-02T10:44:01
**Scope**: All 13 structured CSV files in `dataset/`

---

## 1. Schema Comparison: Actual vs. Input Contract

All files were read successfully. No encoding errors, quoting errors, or malformed rows detected.

| File | Actual Headers | Contract Match | Notes |
| :--- | :--- | :--- | :--- |
| messages.csv | message_id, user_id, conversation_type, group_id, business_id, sender_user_id, created_at, message_text, media_type, media_id, forwarded_count | **MATCH** | — |
| sample_messages.csv | Same + action, message_type, reason, confidence, evidence_message_ids | **EXPECTED SUPERSET** | Input + output schema combined |
| users.csv | user_id, do_not_disturb_window, messages_opened_30d, messages_replied_30d, notifications_dismissed_30d, messages_reported_30d | **MATCH** | |
| groups.csv | group_id, group_name, group_type, member_count, admin_count, created_at, messages_30d | **MATCH** | |
| group_members.csv | group_id, user_id, role, joined_at, messages_sent_30d, messages_read_30d, replies_sent_30d, notifications_dismissed_30d, group_muted_by_user | **MATCH** | `group_muted_by_user` is key signal |
| business_accounts.csv | business_id, display_name, brand_name, category, verified, official_domain, domain_used_by_sender, account_age_days, messages_sent_30d, user_reports_30d, domain_used_by_sender_age_days | **MATCH** | |
| user_business_history.csv | user_id, business_id, relationship_type, first_interaction_date, last_order_date, total_orders, last_booking_date, last_payment_date, opted_in, opted_out, messages_opened_from_business, messages_dismissed_from_business | **MATCH** | `opted_in/opted_out` are personalization signals |
| message_history.csv | message_id, user_id, conversation_type, group_id, business_id, sender_user_id, created_at, message_text, media_type, media_id, forwarded_count | **MATCH** — identical schema to messages.csv | Historical messages |
| message_events.csv | user_id, message_id, message_opened, message_replied, reaction_time_minutes, notification_dismissed, muted_after_message, message_reported | **MATCH** | |
| images.csv | image_id, file_path | **MATCH** | Minimal metadata only (path pointer) |
| voice_notes.csv | voice_note_id, file_path | **MATCH** | Minimal metadata only (path pointer) |
| daily_notification_summary.csv | user_id, date, notifications_received, notifications_opened | **MATCH** | Aggregate volume per user per day |
| output.csv | message_id, action, message_type, reason, confidence, evidence_message_ids | **MATCH** — template only | 110 rows empty except header |

---

## 2. Data Type and Enum Audit

### `messages.csv` — Key Field Types

| Column | Type | Observed Values / Range | Contract Compliance |
| :--- | :--- | :--- | :--- |
| message_id | string | msg_001 to msg_110 range | VERIFIED |
| conversation_type | enum string | personal, group, business | VERIFIED |
| group_id | string or empty | group_001 to group_023 | VERIFIED (empty for non-group) |
| business_id | string or empty | business_001 to business_098 | VERIFIED (empty for non-business) |
| created_at | datetime | 2026-07-18 to 2026-07-31 — all parse to valid dates | VERIFIED |
| media_type | enum or empty | "" / "image" / "voice" | VERIFIED |
| forwarded_count | integer string | 0 to 11 | VERIFIED |

### `business_accounts.csv` — Domain Mismatch Audit

**Key finding**: `official_domain` vs `domain_used_by_sender` differs for accounts with low verification:
- `business_041` (PhonePe): official_domain=`phonepe.com`, sender_domain=`phonepe-rewards.in` (age: 7 days) — **HIGH RISK**
- Short `domain_used_by_sender_age_days` values (<30) = newly registered domains = scam signal.

### `group_members.csv` — `group_muted_by_user` Distribution
- Values observed: `0` (not muted) and `1` (muted). Binary boolean field.
- VERIFIED — correct format.

---

## 3. Discrepancies Between Contract and Actual Schema

| Finding | Severity | Description | Recommended Action |
| :--- | :--- | :--- | :--- |
| `message_history.csv` uses `message_id` not `history_id` | NON-BLOCKING | Identical schema to `messages.csv`. Evidence IDs in output should reference these IDs. | Clarified: historical IDs are prefixed `message_0001` format (not `msg_*`). |
| `message_events.csv` PK is composite `user_id + message_id` | NON-BLOCKING | Documented. No unique single-column PK. | Left-join on both keys. |
| images.csv and voice_notes.csv contain only `image_id/voice_note_id` + `file_path` | NON-BLOCKING | No resolution metadata, dimensions, or duration in CSV — must be read from file. | Phase 2 note: OCR/ASR must process actual binary files. |

---

## 4. Evidence ID Format Note (IMPORTANT)

> Historical messages in `message_history.csv` use IDs like `message_0001`, `message_0002`, etc.
> Incoming messages in `messages.csv` use IDs like `msg_001`, `msg_023`, etc.
> **These are DIFFERENT namespaces** — evidence references in `evidence_message_ids` output column must reference `message_history` IDs (`message_0XXX`), NOT incoming `msg_*` IDs.

This was observed in solved samples (e.g., evidence: `message_0001`, `message_0013;message_0014`).
