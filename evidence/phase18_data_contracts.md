# Phase 18: Input & Data Contracts Specification

## 1. Overview
This specification details the structural contracts, schema definitions, primary keys, foreign key relationships, timestamp fields, and missing data behavior for all 12 dataset files in the **HackerRank Orchestrate Message Notification Router**.

---

## 2. Dataset Contract Specifications

### 2.1 `messages.csv`
- **File Name**: `dataset/messages.csv`
- **Purpose**: Target stream of incoming WhatsApp messages that must be evaluated and routed by the system.
- **Required Fields**: `message_id`, `user_id`, `conversation_type`, `group_id`, `business_id`, `sender_user_id`, `created_at`, `message_text`, `media_type`, `media_id`, `forwarded_count`
- **Primary Key**: `message_id` (format `msg_0XXX`)
- **Foreign Keys**: `user_id` -> `users.csv`, `sender_user_id` -> `users.csv`, `group_id` -> `groups.csv`, `business_id` -> `business_accounts.csv`, `media_id` -> `images.csv` / `voice_notes.csv`
- **Timestamp Field**: `created_at` (ISO 8601 string, e.g. `2026-08-01T14:30:00Z`)
- **Missing Data Behavior**: Optional foreign keys (`group_id`, `business_id`, `media_id`) contain empty string `""` when not applicable. `forwarded_count` defaults to `0` if empty. `message_text` can be empty string `""` for pure media messages.

### 2.2 `output.csv` (and Solved `sample_messages.csv`)
- **File Name**: `dataset/output.csv` & `dataset/sample_messages.csv`
- **Purpose**: Output deliverable template / ground truth solved benchmark containing final routing decisions.
- **Required Fields**: `message_id`, `action`, `message_type`, `reason`, `confidence`, `evidence_message_ids`
- **Primary Key**: `message_id`
- **Foreign Keys**: `message_id` -> `messages.csv`, `evidence_message_ids` -> `message_history.csv`
- **Timestamp Field**: None (inherits `created_at` from `messages.csv`)
- **Missing Data Behavior**: Strict contract. No nulls or empty strings allowed. When no evidence exists, `evidence_message_ids` must be the string `"none"`.

### 2.3 `users.csv`
- **File Name**: `dataset/users.csv`
- **Purpose**: User profile settings, quiet hours preference windows, and global interaction metrics.
- **Required Fields**: `user_id`, `do_not_disturb_window`, `messages_opened_30d`, `messages_replied_30d`, `notifications_dismissed_30d`, `messages_reported_30d`
- **Primary Key**: `user_id` (format `user_0XXX`)
- **Foreign Keys**: None
- **Timestamp Field**: `do_not_disturb_window` stores time range string (e.g. `22:00-07:00`)
- **Missing Data Behavior**: `do_not_disturb_window` can be empty `""` (no quiet hours). Missing interaction counts default to `0`.

### 2.4 `groups.csv`
- **File Name**: `dataset/groups.csv`
- **Purpose**: Group chat metadata, group type, and member count statistics.
- **Required Fields**: `group_id`, `group_name`, `group_type`, `member_count`, `admin_count`, `created_at`, `messages_30d`
- **Primary Key**: `group_id` (format `group_0XXX`)
- **Foreign Keys**: None
- **Timestamp Field**: `created_at`
- **Missing Data Behavior**: Unknown group attributes default to standard broad group policy rules.

### 2.5 `group_members.csv`
- **File Name**: `dataset/group_members.csv`
- **Purpose**: Relationship mapping between users and groups, including admin roles and user group mute settings.
- **Required Fields**: `group_id`, `user_id`, `role`, `joined_at`, `messages_sent_30d`, `messages_read_30d`, `replies_sent_30d`, `notifications_dismissed_30d`, `group_muted_by_user`
- **Primary Key**: Composite (`group_id`, `user_id`)
- **Foreign Keys**: `group_id` -> `groups.csv`, `user_id` -> `users.csv`
- **Timestamp Field**: `joined_at`
- **Missing Data Behavior**: `role` defaults to `"member"` if empty. `group_muted_by_user` defaults to `"false"`.

### 2.6 `business_accounts.csv`
- **File Name**: `dataset/business_accounts.csv`
- **Purpose**: Verified business sender profiles, official domain mapping, and historical spam report statistics.
- **Required Fields**: `business_id`, `display_name`, `brand_name`, `category`, `verified`, `official_domain`, `domain_used_by_sender`, `account_age_days`, `messages_sent_30d`, `user_reports_30d`, `domain_used_by_sender_age_days`
- **Primary Key**: `business_id` (format `biz_0XXX`)
- **Foreign Keys**: None
- **Timestamp Field**: Account age in days (`account_age_days`)
- **Missing Data Behavior**: Unverified businesses default `verified` to `"false"`. Missing domain fields trigger domain-mismatch security analysis.

### 2.7 `user_business_history.csv`
- **File Name**: `dataset/user_business_history.csv`
- **Purpose**: User-specific relationship and opt-in/opt-out status with business senders.
- **Required Fields**: `user_id`, `business_id`, `why_user_knows_account`, `last_activity_at`, `allows_promotions`, `promotions_opted_out_at`, `activity_count_180d`, `messages_opened_30d`, `messages_dismissed_30d`, `messages_replied_30d`, `last_reply_at`
- **Primary Key**: Composite (`user_id`, `business_id`)
- **Foreign Keys**: `user_id` -> `users.csv`, `business_id` -> `business_accounts.csv`
- **Timestamp Field**: `last_activity_at`, `promotions_opted_out_at`, `last_reply_at`
- **Missing Data Behavior**: `allows_promotions` defaults to `"true"` unless `promotions_opted_out_at` contains a valid timestamp or explicit `"false"`.

### 2.8 `message_history.csv`
- **File Name**: `dataset/message_history.csv`
- **Purpose**: Archive of past messages used as candidates for historical evidence selection.
- **Required Fields**: `message_id`, `user_id`, `conversation_type`, `group_id`, `business_id`, `sender_user_id`, `created_at`, `message_text`, `media_type`, `media_id`, `forwarded_count`
- **Primary Key**: `message_id` (format `message_0XXX`)
- **Foreign Keys**: `user_id` -> `users.csv`, `sender_user_id` -> `users.csv`, `group_id` -> `groups.csv`, `business_id` -> `business_accounts.csv`
- **Timestamp Field**: `created_at` (MUST precede incoming message timestamp)
- **Missing Data Behavior**: Messages with timestamps equal to or later than incoming message `created_at` are strictly excluded to prevent future leakage.

### 2.9 `message_events.csv`
- **File Name**: `dataset/message_events.csv`
- **Purpose**: User reaction history for historical messages (replied, dismissed, muted, reported).
- **Required Fields**: `user_id`, `message_id`, `message_opened`, `message_replied`, `reaction_time_minutes`, `notification_dismissed`, `muted_after_message`, `message_reported`
- **Primary Key**: Composite (`user_id`, `message_id`)
- **Foreign Keys**: `user_id` -> `users.csv`, `message_id` -> `message_history.csv`
- **Timestamp Field**: None (inherits from `message_history.csv`)
- **Missing Data Behavior**: Boolean reaction flags default to `"false"` or `"0"`. Missing `reaction_time_minutes` defaults to `null` / empty.

### 2.10 `images.csv`
- **File Name**: `dataset/images.csv`
- **Purpose**: File path lookup table for image poster and screenshot media files.
- **Required Fields**: `image_id`, `file_path`
- **Primary Key**: `image_id` (format `img_0XXX`)
- **Foreign Keys**: `file_path` -> `dataset/media/images/`
- **Timestamp Field**: None
- **Missing Data Behavior**: If file path is invalid or image file is unreadable/corrupt, image processor records `failure=True` and falls back gracefully.

### 2.11 `voice_notes.csv`
- **File Name**: `dataset/voice_notes.csv`
- **Purpose**: File path lookup table for voice note audio files.
- **Required Fields**: `voice_note_id`, `file_path`
- **Primary Key**: `voice_note_id` (format `vn_0XXX`)
- **Foreign Keys**: `file_path` -> `dataset/media/audio/`
- **Timestamp Field**: None
- **Missing Data Behavior**: If audio file is missing or unreadable, voice processor sets `failure=True` and applies fallback penalty.

### 2.12 `daily_notification_summary.csv`
- **File Name**: `dataset/daily_notification_summary.csv`
- **Purpose**: User-level daily notification counts and dismissal volume statistics.
- **Required Fields**: `user_id`, `date`, `notifications_sent`, `notifications_dismissed`
- **Primary Key**: Composite (`user_id`, `date`)
- **Foreign Keys**: `user_id` -> `users.csv`
- **Timestamp Field**: `date` (`YYYY-MM-DD`)
- **Missing Data Behavior**: Missing rows default user notification load to `"normal"`.
