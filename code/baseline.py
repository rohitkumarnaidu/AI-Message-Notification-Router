"""
Main baseline pipeline for Message Notification Router baseline_v1.

Loads dataset messages and context, extracts deterministic features, evaluates routing policy,
selects historical evidence, builds explanations, validates schema and output contracts,
and writes the predictions CSV and trace JSON.

No model calls are made. 0 external API cost.
"""

import argparse
import csv
import json
import logging
import sys
import time
from pathlib import Path

# Add code directory to sys.path to avoid shadowing standard library 'code' module
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import DATASET_DIR
from schemas import OUTPUT_CSV_COLUMNS, ALLOWED_ACTIONS, ALLOWED_MESSAGE_TYPES
from feature_extractor import extract_features
from baseline_policy import route
from evidence_selector import select_evidence
from reason_builder import build_reason
from validators import (
    validate_output_records,
    validate_output_schema,
    validate_row_count_and_ids,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("baseline")


def load_all_context(dataset_dir: Path) -> dict:
    """
    Load all context CSV files from `dataset_dir`.
    Returns a dict mapping filename stem (e.g. 'users', 'groups') to list of row dicts.
    """
    context = {}
    for csv_file in dataset_dir.glob("*.csv"):
        if csv_file.name in ("messages.csv", "sample_messages.csv", "output.csv"):
            continue
        stem = csv_file.stem
        rows = []
        try:
            with open(csv_file, mode="r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception as exc:
            logger.warning("Could not read context file %s: %s", csv_file, exc)
        context[stem] = rows
    return context


def run_baseline(
    messages_path: Path,
    dataset_dir: Path,
    output_path: Path,
    trace_path: Path | None = None,
) -> dict:
    """
    Execute the end-to-end baseline pipeline.

    Returns a stats dictionary with execution metrics.
    """
    start_time = time.time()

    # 1. Schema validation check on expected output columns
    validate_output_schema(OUTPUT_CSV_COLUMNS)

    # 2. Load incoming messages
    if not messages_path.exists():
        raise FileNotFoundError(f"Input messages file not found: {messages_path}")

    input_records = []
    with open(messages_path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            row_copy = dict(row)
            row_copy["_original_index"] = idx
            input_records.append(row_copy)

    logger.info("Loaded %d incoming messages from %s", len(input_records), messages_path)

    # 3. Load all context tables
    context = load_all_context(dataset_dir)
    logger.info("Loaded context tables: %s", ", ".join(context.keys()))

    # 4. Process each message in original order
    output_records = []
    traces = []
    rows_succeeded = 0
    rows_failed = 0

    for idx, msg in enumerate(input_records):
        msg_id = msg.get("message_id", f"unknown_{idx}")
        try:
            features = extract_features(msg, context)
            policy_res = route(features, msg)
            ev_ids = select_evidence(msg, context, max_evidence=3)
            evidence_str = ";".join(ev_ids) if ev_ids else "none"
            reason = build_reason(
                action=policy_res["action"],
                message_type=policy_res["message_type"],
                triggered_rules=policy_res["triggered_rules"],
                features=features,
                msg=msg,
            )

            out_row = {
                "message_id": msg_id,
                "action": policy_res["action"],
                "message_type": policy_res["message_type"],
                "reason": reason,
                "confidence": policy_res["confidence"],
                "evidence_message_ids": evidence_str,
            }
            output_records.append(out_row)
            rows_succeeded += 1

            if trace_path:
                traces.append({
                    "message_id": msg_id,
                    "original_index": idx,
                    "features": {k: v for k, v in features.items() if v},
                    "policy_result": policy_res,
                    "evidence_selected": ev_ids,
                    "reason": reason,
                })

        except Exception as exc:
            logger.warning("Error processing row %d (%s): %s — routing conservatively", idx, msg_id, exc)
            rows_failed += 1
            output_records.append({
                "message_id": msg_id,
                "action": "digest",
                "message_type": "unknown",
                "reason": "Processing error — routed conservatively.",
                "confidence": 0.50,
                "evidence_message_ids": "none",
            })

    # 5. Validate output contracts (schema, IDs, values)
    validate_row_count_and_ids(
        [r.get("message_id") for r in input_records],
        [r.get("message_id") for r in output_records]
    )
    validate_output_records(output_records)

    # 6. Write output CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_CSV_COLUMNS)
        writer.writeheader()
        for row in output_records:
            writer.writerow({
                "message_id": row["message_id"],
                "action": row["action"],
                "message_type": row["message_type"],
                "reason": row["reason"],
                "confidence": f"{float(row['confidence']):.2f}",
                "evidence_message_ids": row["evidence_message_ids"],
            })

    logger.info("Successfully wrote %d baseline output rows to %s", len(output_records), output_path)

    # 7. Write trace JSON if requested
    if trace_path:
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with open(trace_path, mode="w", encoding="utf-8") as f:
            json.dump(
                {
                    "version": "baseline_v1",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "rows_processed": len(input_records),
                    "traces": traces,
                },
                f,
                indent=2,
            )
        logger.info("Wrote trace JSON to %s", trace_path)

    runtime_seconds = round(time.time() - start_time, 3)

    return {
        "rows_processed": len(input_records),
        "rows_succeeded": rows_succeeded,
        "rows_failed": rows_failed,
        "runtime_seconds": runtime_seconds,
        "api_calls": 0,
        "api_cost": 0.0,
    }


def main():
    parser = argparse.ArgumentParser(description="Run Message Notification Router baseline_v1 pipeline.")
    parser.add_argument(
        "--input",
        type=Path,
        default=DATASET_DIR / "messages.csv",
        help="Path to input messages.csv",
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=DATASET_DIR,
        help="Path to dataset directory containing context CSVs",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/baseline_output.csv"),
        help="Path to write baseline predictions CSV",
    )
    parser.add_argument(
        "--trace",
        type=Path,
        default=None,
        help="Optional path to write debug trace JSON",
    )

    args = parser.parse_args()

    try:
        stats = run_baseline(
            messages_path=args.input,
            dataset_dir=args.dataset_dir,
            output_path=args.output,
            trace_path=args.trace,
        )
        print(json.dumps(stats, indent=2))
        sys.exit(0)
    except Exception as exc:
        logger.error("Baseline pipeline failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
