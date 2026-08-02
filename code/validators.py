"""
Validation utilities for Message Notification Router deliverables.
Enforces stable-ID preservation, original-row-order preservation, and schema compliance.
"""

from typing import Iterable

try:
    from schemas import ALLOWED_ACTIONS, ALLOWED_MESSAGE_TYPES, OUTPUT_CSV_COLUMNS
except ImportError:
    from code.schemas import ALLOWED_ACTIONS, ALLOWED_MESSAGE_TYPES, OUTPUT_CSV_COLUMNS


def validate_output_schema(header: list[str] | tuple[str, ...]) -> bool:
    """
    Verify that an output CSV header matches the required OUTPUT_CSV_COLUMNS exactly.
    """
    if tuple(header) != OUTPUT_CSV_COLUMNS:
        raise ValueError(
            f"Output schema mismatch. Expected {OUTPUT_CSV_COLUMNS}, got {tuple(header)}"
        )
    return True


def validate_row_count_and_ids(
    input_ids: list[str], output_ids: list[str]
) -> bool:
    """
    Verify that:
      - input count equals output count
      - input ID list equals output ID list
      - input order equals output order
      - no IDs are dropped
      - no IDs are duplicated
    """
    if len(input_ids) != len(output_ids):
        raise ValueError(
            f"Row count mismatch: input has {len(input_ids)} rows, output has {len(output_ids)} rows"
        )

    if input_ids != output_ids:
        # Check specific reason
        input_set = set(input_ids)
        output_set = set(output_ids)
        if input_set != output_set:
            missing = input_set - output_set
            extra = output_set - input_set
            raise ValueError(
                f"ID set mismatch. Missing IDs: {missing}, Extra IDs: {extra}"
            )
        raise ValueError(
            "ID order mismatch: output row order does not match input row order"
        )

    return True


def validate_action_values(records: list[dict[str, str]]) -> bool:
    """
    Verify that all output records contain a valid action ('notify', 'digest', or 'mute').
    """
    for index, row in enumerate(records, start=1):
        action = row.get("action")
        if action not in ALLOWED_ACTIONS:
            raise ValueError(
                f"Invalid action '{action}' at row {index} (message_id={row.get('message_id')})"
            )
    return True


def validate_message_types(records: list[dict[str, str]]) -> bool:
    """
    Verify that all output records contain a valid message_type per official schema.
    """
    for index, row in enumerate(records, start=1):
        msg_type = row.get("message_type")
        if msg_type not in ALLOWED_MESSAGE_TYPES:
            raise ValueError(
                f"Invalid message_type '{msg_type}' at row {index} (message_id={row.get('message_id')})"
            )
    return True


def validate_confidence_range(records: list[dict[str, str]]) -> bool:
    """
    Verify that confidence is a floating-point number between 0.0 and 1.0 inclusive.
    """
    for index, row in enumerate(records, start=1):
        raw_conf = row.get("confidence")
        try:
            val = float(str(raw_conf))
        except (ValueError, TypeError):
            raise ValueError(
                f"Confidence '{raw_conf}' at row {index} is not a valid float (message_id={row.get('message_id')})"
            )
        if not (0.0 <= val <= 1.0):
            raise ValueError(
                f"Confidence {val} at row {index} out of range [0.0, 1.0] (message_id={row.get('message_id')})"
            )
    return True


def validate_reason_not_empty(records: list[dict[str, str]]) -> bool:
    """
    Verify that reason is a non-empty string.
    """
    for index, row in enumerate(records, start=1):
        reason = (row.get("reason") or "").strip()
        if not reason:
            raise ValueError(
                f"Reason is empty at row {index} (message_id={row.get('message_id')})"
            )
    return True


def validate_evidence_format(records: list[dict[str, str]]) -> bool:
    """
    Verify that evidence_message_ids is either 'none' (case-sensitive) or a semicolon-separated list of IDs.
    """
    for index, row in enumerate(records, start=1):
        ev = (row.get("evidence_message_ids") or "").strip()
        if not ev:
            raise ValueError(
                f"evidence_message_ids cannot be empty at row {index} (use 'none' if no evidence)"
            )
        if ev == "none":
            continue
        # If not 'none', verify semicolon-separated tokens are non-empty
        tokens = [t.strip() for t in ev.split(";")]
        if any(not t for t in tokens):
            raise ValueError(
                f"Invalid evidence_message_ids format '{ev}' at row {index} (message_id={row.get('message_id')})"
            )
    return True


def validate_output_records(records: list[dict[str, str]]) -> bool:
    """
    Run all field-level validators across a list of output records.
    """
    validate_action_values(records)
    validate_message_types(records)
    validate_confidence_range(records)
    validate_reason_not_empty(records)
    validate_evidence_format(records)
    return True
