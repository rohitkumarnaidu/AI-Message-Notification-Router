"""
Tests for Phase 0 architecture-neutral reusable foundations.
Verifies config loading, CSV loading, duplicate detection, and schema/order validation.
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
from validators import validate_action_values, validate_output_schema, validate_row_count_and_ids
from schemas import OUTPUT_CSV_COLUMNS


def test_config_paths_and_placeholders():
    assert DATASET_DIR.exists()
    assert ENV_EXAMPLE_PATH.exists()
    assert validate_env_example_placeholders(ENV_EXAMPLE_PATH) is True


def test_csv_loader_order_and_duplicates():
    messages_path = resolve_dataset_path("messages.csv")
    records = load_csv_records(messages_path)
    assert len(records) > 0
    # Check duplicate detector returns empty list for messages.csv
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

    # Mismatch count
    with pytest.raises(ValueError, match="Row count mismatch"):
        validate_row_count_and_ids(input_ids, ["msg_1", "msg_2"])

    # Mismatch order
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
        {"message_id": "m2", "action": "ignore"},  # invalid
    ]
    with pytest.raises(ValueError, match="Invalid action 'ignore'"):
        validate_action_values(invalid_records)
