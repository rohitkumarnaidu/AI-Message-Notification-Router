"""
Schema definitions and constants for the Message Notification Router dataset and deliverables.
Architecture-neutral constants for input dataset and output contract validation.
"""

# Required columns for dataset/messages.csv
MESSAGES_CSV_COLUMNS = (
    "message_id",
    "user_id",
    "conversation_type",
    "group_id",
    "business_id",
    "sender_user_id",
    "created_at",
    "message_text",
    "media_type",
    "media_id",
    "forwarded_count",
)

# Required columns for dataset/output.csv (and any valid submission output)
OUTPUT_CSV_COLUMNS = (
    "message_id",
    "action",
    "message_type",
    "reason",
    "confidence",
    "evidence_message_ids",
)

# Allowed actions in output contract
ALLOWED_ACTIONS = {"notify", "digest", "mute"}
