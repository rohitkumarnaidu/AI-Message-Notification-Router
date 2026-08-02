# Phase 2 — Cross-File Relationship Audit

**Generated**: 2026-08-02T10:44:01
**Script**: `code/dataset_audit.py`

---

## 1. Relationship Validation Results

All relationships checked using actual dataset files loaded by `code/dataset_audit.py`.

| Relationship | Total Refs | Valid Refs | Missing FK | Invalid FK | Coverage |
| :--- | ---: | ---: | ---: | ---: | :--- |
| messages.user_id -> users.user_id | 110 | 110 | 0 | 0 | **100%** |
| group messages.group_id -> groups.group_id | 63 | 63 | 0 | 0 | **100%** |
| business messages.business_id -> business_accounts.business_id | 30 | 30 | 0 | 0 | **100%** |
| image messages.media_id -> images.image_id | 15 | 15 | 0 | 0 | **100%** |
| voice messages.media_id -> voice_notes.voice_note_id | 8 | 8 | 0 | 0 | **100%** |
| message_events.message_id -> message_history.message_id | 412 | 412 | 0 | 0 | **100%** |

**Overall**: Zero FK violations, zero orphan records, zero ambiguous joins found in official data.

---

## 2. Cardinality Summary

| Join | Cardinality | Risk |
| :--- | :--- | :--- |
| messages LEFT JOIN users (on user_id) | N:1 | Safe — each message has exactly 1 receiver |
| messages LEFT JOIN groups (on group_id) | N:1 | Safe — each group message maps to 1 group |
| messages LEFT JOIN group_members (on user_id + group_id) | N:1 | Safe with composite key |
| messages LEFT JOIN business_accounts (on business_id) | N:1 | Safe — each business message maps to 1 business |
| messages LEFT JOIN user_business_history (on user_id + business_id) | N:0..1 | Safe — not all users have business history |
| messages LEFT JOIN images (on media_id) | N:0..1 | Safe |
| messages LEFT JOIN voice_notes (on media_id) | N:0..1 | Safe |
| message_history LEFT JOIN message_events (on message_id) | 1:1 | Safe (verified 412:412 match) |

---

## 3. Orphan and Ambiguity Report

- **No orphan incoming messages** (all resolve to existing users).
- **No orphan group_member records** detected for incoming messages.
- **No duplicate join rows** detected for composite-key relationships.
- **Potential future risk**: If `user_business_history` is queried without filtering `user_id`, another user's history could attach. Future pipeline must always filter on both `user_id` AND `business_id`.

---

## 4. Safe Join Recommendations

> Do not implement final pipeline joins yet. These are constraints for Phase 3+.

1. **Always `LEFT JOIN` from `messages.csv`**: Never inner join; personal messages have no group/business FK.
2. **Assign `original_index` before any join**: `[0, 1, 2, ..., 109]` to protect order.
3. **Validate post-join row count**: After every join, assert `len(result) == 110`.
4. **Use composite keys for group_members**: `(user_id, group_id)` — never join on `user_id` alone.
5. **Use composite keys for user_business_history**: `(user_id, business_id)` — never join on `business_id` alone.
6. **Never attach future history**: Filter `message_history.created_at` to be ≤ `messages.created_at` for the same user.
7. **Deduplicate evidence candidates**: After retrieval, ensure `evidence_message_ids` contains unique values only.

---

## 5. Evidence ID Namespace Clarification

**CRITICAL**: Historical message IDs (`message_history.csv`) use the format `message_0001`...`message_0412`. Incoming message IDs (`messages.csv`) use the format `msg_001`...`msg_110`. These are **mutually exclusive namespaces**.

- The `evidence_message_ids` output column MUST reference `message_history.csv` IDs only.
- Referencing an incoming `msg_*` ID as evidence is an error (future history leakage or self-reference).
- Verified in `sample_messages.csv`: evidence column contains `message_0001`, `message_0013;message_0014`, `none` — never `msg_*`.
