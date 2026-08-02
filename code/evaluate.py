"""
Evaluation harness for Message Notification Router baseline_v1.
Evaluates baseline predictions against labeled solved samples (sample_messages.csv).
Never computes accuracy or F1 on unlabeled messages.
Checks full output integrity across all 110 messages.
"""

import argparse
import csv
import json
import logging
import sys
from collections import Counter, defaultdict
import sys
from pathlib import Path

# Add code directory to sys.path to avoid shadowing standard library 'code' module
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import DATASET_DIR
from schemas import OUTPUT_CSV_COLUMNS, ALLOWED_ACTIONS, ALLOWED_MESSAGE_TYPES
from validators import (
    validate_output_records,
    validate_output_schema,
    validate_row_count_and_ids,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("evaluate")


def load_sample_predictions(
    sample_path: Path, output_path: Path
) -> tuple[list[dict], list[dict]]:
    """
    Load solved samples and match them with corresponding output rows by message_id.
    Returns (matched_true_rows, matched_pred_rows).
    """
    if not sample_path.exists() or not output_path.exists():
        raise FileNotFoundError(f"Missing sample ({sample_path}) or output ({output_path}) file")

    true_by_id = {}
    with open(sample_path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            true_by_id[row["message_id"]] = row

    pred_by_id = {}
    with open(output_path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pred_by_id[row["message_id"]] = row

    matched_true = []
    matched_pred = []

    for msg_id, true_row in true_by_id.items():
        if msg_id in pred_by_id:
            matched_true.append(true_row)
            matched_pred.append(pred_by_id[msg_id])
        else:
            logger.warning("Sample message_id %s not found in predictions", msg_id)

    return matched_true, matched_pred


def _compute_metrics_for_classes(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict:
    """Helper to compute precision, recall, F1, accuracy, and confusion matrix."""
    n = len(y_true)
    if n == 0:
        return {"accuracy": 0.0, "macro_f1": 0.0, "per_class": {}, "confusion_matrix": {}}

    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = round(correct / n, 4)

    # Confusion matrix
    cm = {l1: {l2: 0 for l2 in labels} for l1 in labels}
    for t, p in zip(y_true, y_pred):
        if t in cm and p in cm[t]:
            cm[t][p] += 1
        elif t in cm:
            cm[t]["OTHER"] = cm[t].get("OTHER", 0) + 1

    per_class = {}
    f1_sum = 0.0
    valid_classes = 0

    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)

        precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
        recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
        f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0

        support = sum(1 for t in y_true if t == label)
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        }
        if support > 0:
            f1_sum += f1
            valid_classes += 1

    macro_f1 = round(f1_sum / max(valid_classes, 1), 4)

    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "per_class": per_class,
        "confusion_matrix": cm,
    }


def compute_action_metrics(y_true: list[str], y_pred: list[str]) -> dict:
    """Compute accuracy, per-class P/R/F1, macro F1, and confusion matrix for action."""
    labels = sorted(list(ALLOWED_ACTIONS))
    return _compute_metrics_for_classes(y_true, y_pred, labels)


def compute_type_metrics(y_true: list[str], y_pred: list[str]) -> dict:
    """Compute accuracy, per-class P/R/F1, macro F1, and confusion matrix for message_type."""
    labels = sorted(list(ALLOWED_MESSAGE_TYPES))
    return _compute_metrics_for_classes(y_true, y_pred, labels)


def compute_output_integrity(input_records: list[dict], output_records: list[dict]) -> dict:
    """
    Verify schema validity, row counts, ID matching, and order preservation across ALL messages.
    """
    total_in = len(input_records)
    total_out = len(output_records)

    row_count_match = total_in == total_out
    in_ids = [r.get("message_id") for r in input_records]
    out_ids = [r.get("message_id") for r in output_records]

    ids_match = sorted(in_ids) == sorted(out_ids)
    order_match = in_ids == out_ids

    valid_rows = 0
    invalid_rows = 0
    for row in output_records:
        try:
            validate_output_records([row])
            valid_rows += 1
        except Exception:
            invalid_rows += 1

    schema_valid_rate = round(valid_rows / max(total_out, 1), 4)

    return {
        "total_input_rows": total_in,
        "total_output_rows": total_out,
        "row_count_match": row_count_match,
        "ids_match": ids_match,
        "order_match": order_match,
        "schema_valid_rate": schema_valid_rate,
        "invalid_row_count": invalid_rows,
    }


def run_evaluation(
    sample_path: Path,
    messages_path: Path,
    baseline_output_path: Path,
    report_path: Path,
) -> dict:
    """
    Run full baseline evaluation on solved samples and integrity check on all messages.
    Writes JSON report to `report_path`.
    """
    # 1. Load all incoming messages and output records for integrity check
    input_records = []
    with open(messages_path, mode="r", encoding="utf-8", newline="") as f:
        for idx, row in enumerate(csv.DictReader(f)):
            input_records.append(dict(row))

    output_records = []
    with open(baseline_output_path, mode="r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            output_records.append(dict(row))

    integrity = compute_output_integrity(input_records, output_records)

    # 2. Match labeled samples
    matched_true, matched_pred = load_sample_predictions(sample_path, baseline_output_path)

    y_true_action = [r["action"] for r in matched_true]
    y_pred_action = [r["action"] for r in matched_pred]

    y_true_type = [r["message_type"] for r in matched_true]
    y_pred_type = [r["message_type"] for r in matched_pred]

    action_metrics = compute_action_metrics(y_true_action, y_pred_action)
    type_metrics = compute_type_metrics(y_true_type, y_pred_type)

    # 3. Analyze confidence distribution
    confidences = [float(r["confidence"]) for r in output_records]
    avg_conf = round(sum(confidences) / max(len(confidences), 1), 4)
    min_conf = round(min(confidences), 4) if confidences else 0.0
    max_conf = round(max(confidences), 4) if confidences else 0.0

    # 4. Error analysis on solved samples (misclassified IDs)
    misclassified_action = []
    misclassified_type = []
    for t, p in zip(matched_true, matched_pred):
        if t["action"] != p["action"]:
            misclassified_action.append({
                "message_id": t["message_id"],
                "true_action": t["action"],
                "pred_action": p["action"],
                "reason": p["reason"],
            })
        if t["message_type"] != p["message_type"]:
            misclassified_type.append({
                "message_id": t["message_id"],
                "true_type": t["message_type"],
                "pred_type": p["message_type"],
                "reason": p["reason"],
            })

    report = {
        "version": "baseline_v1",
        "sample_count": len(matched_true),
        "total_messages_count": len(output_records),
        "action_metrics": action_metrics,
        "type_metrics": type_metrics,
        "output_integrity": integrity,
        "confidence_stats": {
            "average": avg_conf,
            "min": min_conf,
            "max": max_conf,
        },
        "misclassified_action_samples": misclassified_action,
        "misclassified_type_samples": misclassified_type,
    }

    # Write JSON report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, mode="w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info("Evaluation report written to %s", report_path)
    logger.info("Action Accuracy on solved samples: %.4f", action_metrics["accuracy"])
    logger.info("Action Macro F1 on solved samples: %.4f", action_metrics["macro_f1"])

    return report


def main():
    parser = argparse.ArgumentParser(description="Evaluate Message Notification Router baseline_v1.")
    parser.add_argument(
        "--sample",
        type=Path,
        default=DATASET_DIR / "sample_messages.csv",
        help="Path to labeled sample_messages.csv",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DATASET_DIR / "messages.csv",
        help="Path to full messages.csv",
    )
    parser.add_argument(
        "--baseline-output",
        type=Path,
        default=Path("outputs/baseline_output.csv"),
        help="Path to baseline predictions CSV",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("evaluation/baseline_v1_report.json"),
        help="Path to write evaluation report JSON",
    )

    args = parser.parse_args()

    try:
        report = run_evaluation(
            sample_path=args.sample,
            messages_path=args.input,
            baseline_output_path=args.baseline_output,
            report_path=args.report,
        )
        print(
            f"\n--- EVALUATION SUMMARY ---\n"
            f"Action Accuracy : {report['action_metrics']['accuracy']:.4f}\n"
            f"Action Macro F1 : {report['action_metrics']['macro_f1']:.4f}\n"
            f"Type Accuracy   : {report['type_metrics']['accuracy']:.4f}\n"
            f"Type Macro F1   : {report['type_metrics']['macro_f1']:.4f}\n"
            f"Output Integrity: {report['output_integrity']['schema_valid_rate']*100:.1f}% valid\n"
        )
        sys.exit(0)
    except Exception as exc:
        logger.error("Evaluation failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
