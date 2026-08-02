"""
Validation utilities for Message Notification Router deliverables.
Enforces stable-ID preservation, original-row-order preservation, and schema compliance.
"""

from typing import Iterable

try:
    from schemas import ALLOWED_ACTIONS, OUTPUT_CSV_COLUMNS
except ImportError:
    from code.schemas import ALLOWED_ACTIONS, OUTPUT_CSV_COLUMNS


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
