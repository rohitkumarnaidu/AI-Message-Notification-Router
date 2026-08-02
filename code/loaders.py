"""
Data loading and parsing utilities for Message Notification Router.
Provides architecture-neutral CSV, JSON, and text loading with order preservation and duplicate detection.
"""

import csv
import json
from pathlib import Path
from typing import Any


def load_csv_records(filepath: Path | str) -> list[dict[str, str]]:
    """
    Load CSV records as a list of dictionaries, preserving original row order.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with open(path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def find_duplicate_ids(
    records: list[dict[str, str]], id_field: str = "message_id"
) -> list[str]:
    """
    Detect duplicate IDs in a list of dictionary records.
    Returns a list of duplicate ID values in order of second appearance.
    """
    seen = set()
    duplicates = []
    for row in records:
        val = row.get(id_field)
        if val in seen:
            if val not in duplicates:
                duplicates.append(val)
        else:
            seen.add(val)
    return duplicates


def load_json_data(filepath: Path | str) -> Any:
    """
    Load JSON data safely, raising ValueError if content is malformed.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    try:
        with open(path, mode="r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in {path}: {exc}") from exc


def read_utf8_text(filepath: Path | str) -> str:
    """Read file content cleanly in UTF-8."""
    path = Path(filepath)
    with open(path, mode="r", encoding="utf-8") as f:
        return f.read()

def load_full_dataset(dataset_dir: Path | str) -> dict[str, list[dict[str, str]]]:
    """Loads all expected CSV files into a unified dictionary."""
    base_path = Path(dataset_dir)
    context = {}
    expected_files = [
        "messages.csv", "users.csv", "groups.csv", "group_members.csv", 
        "business_accounts.csv", "user_business_history.csv", 
        "message_history.csv", "message_events.csv", 
        "images.csv", "voice_notes.csv"
    ]
    for filename in expected_files:
        filepath = base_path / filename
        key = filename.replace(".csv", "")
        if filepath.exists():
            context[key] = load_csv_records(filepath)
        else:
            context[key] = []
    return context
