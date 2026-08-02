"""
Evaluation harness for Message Notification Router.
Supports explicit modes: solved, structural, unlabeled-audit, media-subset.
"""

import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from collections import defaultdict, Counter

# Add code directory to sys.path to avoid shadowing standard library 'code' module
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import DATASET_DIR
from schemas import OUTPUT_CSV_COLUMNS, ALLOWED_ACTIONS, ALLOWED_MESSAGE_TYPES
from validators import validate_output_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("evaluate")

def load_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    records = []
    with open(path, mode="r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(dict(row))
    return records

def _compute_metrics_for_classes(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict:
    accuracy = sum(1 for t, p in zip(y_true, y_pred) if t == p) / max(len(y_true), 1)
    cm = {label: {l: 0 for l in labels} for label in labels}
    for label in labels:
        cm[label]["OTHER"] = 0
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
    return {"accuracy": accuracy, "macro_f1": macro_f1, "per_class": per_class, "confusion_matrix": cm}

def evaluate_solved(expected_records: list[dict], pred_records: list[dict]) -> dict:
    # Requires matching counts, ids, order
    if len(expected_records) != len(pred_records):
        raise ValueError(f"Solved mode requires matching row count. expected={len(expected_records)}, pred={len(pred_records)}")
    
    exp_ids = [r["message_id"] for r in expected_records]
    pred_ids = [r["message_id"] for r in pred_records]
    
    if len(set(exp_ids)) != len(exp_ids):
        raise ValueError("Duplicate expected IDs")
    if len(set(pred_ids)) != len(pred_ids):
        raise ValueError("Duplicate prediction IDs")
        
    if exp_ids != pred_ids:
        raise ValueError("ID sets or order do not match between expected and predicted.")
        
    y_true_action = [r["action"] for r in expected_records]
    y_pred_action = [r["action"] for r in pred_records]
    y_true_type = [r["message_type"] for r in expected_records]
    y_pred_type = [r["message_type"] for r in pred_records]

    action_metrics = _compute_metrics_for_classes(y_true_action, y_pred_action, sorted(list(ALLOWED_ACTIONS)))
    type_metrics = _compute_metrics_for_classes(y_true_type, y_pred_type, sorted(list(ALLOWED_MESSAGE_TYPES)))

    return {
        "sample_count": len(expected_records),
        "action_metrics": action_metrics,
        "type_metrics": type_metrics,
    }

def evaluate_structural(input_records: list[dict], pred_records: list[dict]) -> dict:
    if len(input_records) != len(pred_records):
        raise ValueError(f"Structural mode requires matching row count. input={len(input_records)}, pred={len(pred_records)}")
    
    in_ids = [r["message_id"] for r in input_records]
    pred_ids = [r["message_id"] for r in pred_records]
    
    if len(set(in_ids)) != len(in_ids):
        raise ValueError("Duplicate input IDs")
    if len(set(pred_ids)) != len(pred_ids):
        raise ValueError("Duplicate prediction IDs")
        
    if in_ids != pred_ids:
        raise ValueError("ID sets or order do not match between input and predicted.")

    valid_rows = 0
    invalid_rows = 0
    for row in pred_records:
        try:
            validate_output_records([row])
            valid_rows += 1
        except Exception:
            invalid_rows += 1
            
    return {
        "total_rows": len(pred_records),
        "schema_valid_rate": valid_rows / max(len(pred_records), 1),
        "invalid_row_count": invalid_rows,
        "structural_pass": invalid_rows == 0
    }

def evaluate_unlabeled_audit(input_records: list[dict], pred_records: list[dict]) -> dict:
    structural = evaluate_structural(input_records, pred_records)
    if not structural["structural_pass"]:
        raise ValueError("Unlabeled audit failed structural checks.")

    actions = [r["action"] for r in pred_records]
    types = [r["message_type"] for r in pred_records]
    confs = [float(r["confidence"]) for r in pred_records]
    
    return {
        "total_rows": len(pred_records),
        "action_distribution": dict(Counter(actions)),
        "type_distribution": dict(Counter(types)),
        "confidence_stats": {
            "min": min(confs) if confs else 0,
            "max": max(confs) if confs else 0,
            "avg": sum(confs) / len(confs) if confs else 0
        },
        "structural": structural
    }

def evaluate_media_subset(subset_input: list[dict], pred_records: list[dict], expected_records: list[dict] = None) -> dict:
    if len(subset_input) != len(pred_records):
        raise ValueError(f"Media subset mode requires matching row count. input={len(subset_input)}, pred={len(pred_records)}")
        
    in_ids = [r["message_id"] for r in subset_input]
    pred_ids = [r["message_id"] for r in pred_records]
    
    if in_ids != pred_ids:
        raise ValueError("ID sets or order do not match between subset input and predicted.")
        
    report = {"total_rows": len(pred_records)}
    report["structural"] = evaluate_structural(subset_input, pred_records)
    
    if expected_records:
        # Match expected to subset
        expected_dict = {r["message_id"]: r for r in expected_records}
        matched_expected = []
        for pid in pred_ids:
            if pid not in expected_dict:
                raise ValueError(f"Expected labels missing for message {pid}")
            matched_expected.append(expected_dict[pid])
            
        report["solved"] = evaluate_solved(matched_expected, pred_records)
        
    return report

def main():
    parser = argparse.ArgumentParser(description="Evaluate Message Notification Router predictions.")
    parser.add_argument("--mode", type=str, required=True, choices=["solved", "structural", "unlabeled-audit", "media-subset"])
    parser.add_argument("--input", type=Path, help="Path to input source messages.csv")
    parser.add_argument("--expected", type=Path, help="Path to expected labels (e.g. sample_messages.csv)")
    parser.add_argument("--output", type=Path, required=True, help="Path to prediction output CSV")
    parser.add_argument("--report", type=Path, required=True, help="Path to write JSON report")
    args = parser.parse_args()

    try:
        pred_records = load_csv(args.output)
        
        # Guard against using prediction file as source input
        if args.input and args.input.resolve() == args.output.resolve():
            raise ValueError("Prediction file supplied as source input.")
            
        report_data = {"mode": args.mode, "version": "v2"}
        
        if args.mode == "solved":
            if not args.expected:
                raise ValueError("--expected is required for solved mode")
            expected_records = load_csv(args.expected)
            report_data.update(evaluate_solved(expected_records, pred_records))
            
        elif args.mode == "structural":
            if not args.input:
                raise ValueError("--input is required for structural mode")
            input_records = load_csv(args.input)
            report_data.update(evaluate_structural(input_records, pred_records))
            
        elif args.mode == "unlabeled-audit":
            if not args.input:
                raise ValueError("--input is required for unlabeled-audit mode")
            input_records = load_csv(args.input)
            report_data.update(evaluate_unlabeled_audit(input_records, pred_records))
            
        elif args.mode == "media-subset":
            if not args.input:
                raise ValueError("--input is required for media-subset mode")
            input_records = load_csv(args.input)
            expected_records = load_csv(args.expected) if args.expected else None
            report_data.update(evaluate_media_subset(input_records, pred_records, expected_records))

        args.report.parent.mkdir(parents=True, exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
            
        logger.info(f"Successfully generated {args.mode} report at {args.report}")
        sys.exit(0)
    except Exception as exc:
        logger.error("Evaluation failed: %s", exc)
        sys.exit(1)

if __name__ == "__main__":
    main()
