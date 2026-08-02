# Phase 2 — Temporal Integrity and Personalization Audit

**Generated**: 2026-08-02T10:44:01

---

## Temporal Integrity Audit

### Timestamp Parse Results
- `messages.csv.created_at`: **110/110 parsed** (0 missing, 0 future)
- `message_history.csv.created_at`: **412/412 parsed** (0 missing, 0 future)
- All messages fall in range 2026-07-18 to 2026-07-31.
- All historical messages predate 2026-08-01 at file level.

### Row-Level Future Leakage Check
- Not yet verified at row level (deferred to Phase 3 retrieval implementation).
- **Constraint for Phase 3**: When retrieving evidence for message `msg_X` (timestamp `T`), only include `message_history` rows where `created_at <= T` for the same `user_id`.

### Quiet Hours (DND Window)
- Format: `HH:MM-HH:MM` (e.g., `22:00-07:00`).
- Cross-midnight windows (e.g., 22:00-07:00) require date arithmetic: if DND_start > DND_end, the window spans midnight.
- All 54 users have a DND window defined.
- No messages have null timestamps — DND check is always possible.

### Deadline Extraction Risk
- Several messages mention same-day deadlines embedded in text ("closes at 5 PM today", "before midnight").
- Date extraction from text is required for accurate urgency classification but is not yet implemented.

---

## Personalization Audit

### User-Level Signal Coverage

| User Signal | Source | Coverage | Signal Strength |
| :--- | :--- | :--- | :--- |
| DND (quiet hours) | users.csv | 100% (54/54) | HIGH — structural preference |
| messages_opened_30d | users.csv | 100% | MEDIUM — aggregate, not per-sender |
| messages_replied_30d | users.csv | 100% | HIGH — reply is strong engagement |
| notifications_dismissed_30d | users.csv | 100% | HIGH — dismissal = low interest |
| messages_reported_30d | users.csv | 100% | CRITICAL — any report = safety signal |

**Sparse-context users**: u_040 (17 opens, 2 replies, 81 dismissals, 4 reports) is a low-engagement, high-dismissal, high-report user. Safe default: digest or mute for new/unvetted content.

### Group Membership Signal Coverage

| Signal | Source | Notes |
| :--- | :--- | :--- |
| Role (admin/member) | group_members.csv | Key for trust weighting |
| group_muted_by_user | group_members.csv | Direct mute override |
| messages_read_30d | group_members.csv | Per-group engagement |
| replies_sent_30d | group_members.csv | Per-group participation |
| notifications_dismissed_30d | group_members.csv | Per-group dismissal |

### Business Relationship Signal Coverage

| Signal | Source | Notes |
| :--- | :--- | :--- |
| opted_in / opted_out | user_business_history.csv | Critical for promo routing |
| last_order_date | user_business_history.csv | Recency of relationship |
| last_payment_date | user_business_history.csv | Active transactional user |
| messages_opened_from_business | user_business_history.csv | Business-specific engagement |
| messages_dismissed_from_business | user_business_history.csv | Business-specific dismissal |

**Coverage**: 106 user-business history rows for 110 business messages. ~4 business messages may have no relationship history — treat as new/unknown relationship.

### Historical Behavioral Coverage
- 412 historical message_events cover 412 message_history rows.
- 1-to-1 mapping confirmed.
- **Sparse-history risk**: Users with few historical records will have lower behavioral confidence.
- **Contradictory behavior risk**: If user opened and later reported similar messages, weight the report more heavily (safety-first).
