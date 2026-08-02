"""
Tests for Phase 0 architecture-neutral reusable foundations and Phase 1 contract validators.
Verifies config loading, CSV loading, duplicate detection, and schema/order/field-level validation.
"""

import sys
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CODE_DIR = REPO_ROOT / "code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from config import DATASET_DIR, ENV_EXAMPLE_PATH, resolve_dataset_path, validate_env_example_placeholders
from loaders import find_duplicate_ids, load_csv_records
from validators import (
    validate_action_values,
    validate_confidence_range,
    validate_evidence_format,
    validate_message_types,
    validate_output_records,
    validate_output_schema,
    validate_reason_not_empty,
    validate_row_count_and_ids,
)
from schemas import OUTPUT_CSV_COLUMNS


def test_config_paths_and_placeholders():
    assert DATASET_DIR.exists()
    assert ENV_EXAMPLE_PATH.exists()
    assert validate_env_example_placeholders(ENV_EXAMPLE_PATH) is True


def test_csv_loader_order_and_duplicates():
    messages_path = resolve_dataset_path("messages.csv")
    records = load_csv_records(messages_path)
    assert len(records) > 0
    dups = find_duplicate_ids(records, id_field="message_id")
    assert dups == []


def test_find_duplicate_ids_with_dups():
    fake_records = [
        {"message_id": "msg_1", "val": "a"},
        {"message_id": "msg_2", "val": "b"},
        {"message_id": "msg_1", "val": "c"},
    ]
    dups = find_duplicate_ids(fake_records, id_field="message_id")
    assert dups == ["msg_1"]


def test_validate_output_schema_pass_and_fail():
    assert validate_output_schema(list(OUTPUT_CSV_COLUMNS)) is True
    with pytest.raises(ValueError, match="Output schema mismatch"):
        validate_output_schema(["message_id", "wrong_col"])


def test_validate_row_count_and_ids():
    input_ids = ["msg_1", "msg_2", "msg_3"]
    output_ids = ["msg_1", "msg_2", "msg_3"]
    assert validate_row_count_and_ids(input_ids, output_ids) is True

    with pytest.raises(ValueError, match="Row count mismatch"):
        validate_row_count_and_ids(input_ids, ["msg_1", "msg_2"])

    with pytest.raises(ValueError, match="ID order mismatch"):
        validate_row_count_and_ids(input_ids, ["msg_2", "msg_1", "msg_3"])


def test_validate_action_values():
    valid_records = [
        {"message_id": "m1", "action": "notify"},
        {"message_id": "m2", "action": "digest"},
        {"message_id": "m3", "action": "mute"},
    ]
    assert validate_action_values(valid_records) is True

    invalid_records = [
        {"message_id": "m1", "action": "notify"},
        {"message_id": "m2", "action": "ignore"},
    ]
    with pytest.raises(ValueError, match="Invalid action 'ignore'"):
        validate_action_values(invalid_records)


def test_validate_message_types():
    valid_records = [
        {"message_id": "m1", "message_type": "personal"},
        {"message_id": "m2", "message_type": "scam"},
        {"message_id": "m3", "message_type": "unknown"},
    ]
    assert validate_message_types(valid_records) is True

    invalid_records = [
        {"message_id": "m1", "message_type": "invalid_type"},
    ]
    with pytest.raises(ValueError, match="Invalid message_type 'invalid_type'"):
        validate_message_types(invalid_records)


def test_validate_confidence_range():
    valid_records = [
        {"message_id": "m1", "confidence": "0"},
        {"message_id": "m2", "confidence": "0.85"},
        {"message_id": "m3", "confidence": 1.0},
    ]
    assert validate_confidence_range(valid_records) is True

    with pytest.raises(ValueError, match="out of range"):
        validate_confidence_range([{"message_id": "m1", "confidence": "1.5"}])
    with pytest.raises(ValueError, match="out of range"):
        validate_confidence_range([{"message_id": "m1", "confidence": "-0.1"}])


def test_validate_reason_not_empty():
    valid_records = [{"message_id": "m1", "reason": "Important message from boss"}]
    assert validate_reason_not_empty(valid_records) is True

    with pytest.raises(ValueError, match="Reason is empty"):
        validate_reason_not_empty([{"message_id": "m1", "reason": "   "}])


def test_validate_evidence_format():
    valid_records = [
        {"message_id": "m1", "evidence_message_ids": "none"},
        {"message_id": "m2", "evidence_message_ids": "msg_12; msg_15"},
    ]
    assert validate_evidence_format(valid_records) is True

    with pytest.raises(ValueError, match="cannot be empty"):
        validate_evidence_format([{"message_id": "m1", "evidence_message_ids": ""}])


def test_validate_output_records_complete():
    valid_records = [
        {
            "message_id": "m1",
            "action": "notify",
            "message_type": "urgent",
            "reason": "Direct mention in active group",
            "confidence": "0.95",
            "evidence_message_ids": "msg_10",
        },
        {
            "message_id": "m2",
            "action": "mute",
            "message_type": "scam",
            "reason": "Suspicious payment link from unknown sender",
            "confidence": "0.99",
            "evidence_message_ids": "none",
        },
    ]
    assert validate_output_records(valid_records) is True
