import csv
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = REPO_ROOT / "dataset"


def test_messages_csv_exists_and_not_empty():
    messages_path = DATASET_DIR / "messages.csv"
    assert messages_path.exists(), "dataset/messages.csv must exist"
    with open(messages_path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        assert header is not None, "messages.csv must have a header row"
        rows = list(reader)
        assert len(rows) > 0, "messages.csv must contain at least one message row"


def test_messages_csv_unique_ids():
    messages_path = DATASET_DIR / "messages.csv"
    with open(messages_path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        message_ids = [row["message_id"] for row in reader]
    assert len(message_ids) == len(
        set(message_ids)
    ), "All message_id entries in messages.csv must be unique"


def test_messages_csv_required_columns():
    expected_cols = [
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
    ]
    messages_path = DATASET_DIR / "messages.csv"
    with open(messages_path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
    assert header == expected_cols, (
        f"messages.csv columns mismatch. Expected {expected_cols}, got {header}"
    )


def test_output_csv_template_schema():
    expected_cols = [
        "message_id",
        "action",
        "message_type",
        "reason",
        "confidence",
        "evidence_message_ids",
    ]
    output_path = DATASET_DIR / "output.csv"
    assert output_path.exists(), "dataset/output.csv must exist"
    with open(output_path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
    assert header == expected_cols, (
        f"output.csv columns mismatch. Expected {expected_cols}, got {header}"
    )


def test_sample_messages_csv_schema_and_values():
    expected_cols = [
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
        "action",
        "message_type",
        "reason",
        "confidence",
        "evidence_message_ids",
    ]
    sample_path = DATASET_DIR / "sample_messages.csv"
    assert sample_path.exists(), "dataset/sample_messages.csv must exist"
    allowed_actions = {"notify", "digest", "mute"}
    with open(sample_path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == expected_cols
        for row in reader:
            assert row["action"] in allowed_actions, (
                f"Invalid action {row['action']} in sample_messages.csv"
            )


def test_required_dataset_files_present():
    required_files = [
        "users.csv",
        "groups.csv",
        "group_members.csv",
        "business_accounts.csv",
        "user_business_history.csv",
        "message_history.csv",
        "message_events.csv",
        "images.csv",
        "voice_notes.csv",
        "daily_notification_summary.csv",
    ]
    for filename in required_files:
        filepath = DATASET_DIR / filename
        assert filepath.exists(), f"Required dataset file {filename} is missing"
