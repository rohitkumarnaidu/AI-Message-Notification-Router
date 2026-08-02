# Phase 1 Input Contract Specification

## 1. Dataset Overview & File Schemas
All participant-facing input files reside under `dataset/`. All CSV files are UTF-8 encoded with standard comma delimiters.

### 1.1 `dataset/messages.csv` (Primary Routing Input)
- **Purpose**: Incoming WhatsApp messages requiring routing predictions.
- **Primary Key**: `message_id`
- **Columns**:
  - `message_id`: string, unique ID
  - `user_id`: string, receiving user ID (FK -> `users.csv`)
  - `conversation_type`: string, allowed: `personal`, `group`, `business`
  - `group_id`: string, optional group ID (FK -> `groups.csv`)
  - `business_id`: string, optional business ID (FK -> `business_accounts.csv`)
  - `sender_user_id`: string, optional sender ID
  - `created_at`: timestamp string
  - `message_text`: text string (empty if media_type is voice)
  - `media_type`: string, allowed: empty string, `image`, `voice`
  - `media_id`: string, optional media ID (FK -> `images.csv` or `voice_notes.csv`)
  - `forwarded_count`: integer string

### 1.2 Supplementary Context CSVs
- **`dataset/users.csv`**: PK `user_id`; contains quiet hours, recent open/reply/dismiss/report rates.
- **`dataset/groups.csv`**: PK `group_id`; contains group type, size, admin count, activity metrics.
- **`dataset/group_members.csv`**: Composite key (`user_id`, `group_id`); contains role, reply rate, mute state.
- **`dataset/business_accounts.csv`**: PK `business_id`; brand identity, verification status, sender domain, spam report counts.
- **`dataset/user_business_history.csv`**: Composite key (`user_id`, `business_id`); orders, bookings, payment history, opt-in status.
- **`dataset/message_history.csv`**: PK `message_id`; historical messages received by users.
- **`dataset/message_events.csv`**: FK `message_id`, `user_id`; user reactions (opened, replied, dismissed, muted, reported).
- **`dataset/images.csv`**: PK `image_id`; maps to media file path under `dataset/media/images/`.
- **`dataset/voice_notes.csv`**: PK `voice_note_id`; maps to media file path under `dataset/media/audio/`.
- **`dataset/daily_notification_summary.csv`**: FK `user_id`; daily notification volume and load.
- **`dataset/sample_messages.csv`**: Solved example rows for schema reference only.
- **`dataset/output.csv`**: Blank submission template with 6 headers.

---

## 2. Entity Relationship Map

```text
incoming message (messages.csv)
  ├── receiving user            -> users.csv (user_id)
  ├── sender user               -> users.csv (sender_user_id)
  ├── group conversation        -> groups.csv (group_id)
  ├── group membership          -> group_members.csv (user_id, group_id)
  ├── business sender           -> business_accounts.csv (business_id)
  ├── user-business relationship-> user_business_history.csv (user_id, business_id)
  ├── image media               -> images.csv (media_id -> dataset/media/images/...)
  └── voice media               -> voice_notes.csv (media_id -> dataset/media/audio/...)

historical message (message_history.csv)
  └── historical reaction event -> message_events.csv (message_id, user_id)
```

---

## 3. Input Invariants
1. **Unique ID Integrity**: Every row in `dataset/messages.csv` has a unique, non-null `message_id`.
2. **Read-Only Data Protection**: Official files under `dataset/` must never be modified or overwritten during execution.
3. **Optional Context Resilience**: Missing optional foreign keys (`group_id` in personal chats, `business_id` in group chats) must be parsed cleanly as empty/null without crashing.
4. **Stable Row Order**: Rows loaded from `messages.csv` maintain their exact sequence (`original_index`) for 1-to-1 output alignment.
