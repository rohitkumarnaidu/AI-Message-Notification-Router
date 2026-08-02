"""
Minimal Phase 0 CLI entry-point skeleton for Message Notification Router.
Provides diagnostic checks for configuration, dataset paths, and data-integrity foundations.
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CODE_DIR = REPO_ROOT / "code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import DATASET_DIR, resolve_dataset_path, validate_env_example_placeholders
from loaders import find_duplicate_ids, load_csv_records
from validators import validate_output_schema
from hybrid_pipeline import run_pipeline


def run_diagnostic_check() -> int:
    """Run Phase 0 repository and data-integrity diagnostic check."""
    try:
        print("Running Phase 0 Diagnostic Check...")

        # 1. Validate .env.example placeholders
        validate_env_example_placeholders()
        print("[PASS] .env.example verified (placeholders only, no real secrets)")

        # 2. Check messages.csv
        messages_path = resolve_dataset_path("messages.csv")
        messages = load_csv_records(messages_path)
        print(f"[PASS] Loaded {len(messages)} rows from dataset/messages.csv")

        # 3. Check duplicate IDs
        duplicates = find_duplicate_ids(messages, id_field="message_id")
        if duplicates:
            print(f"[FAIL] Found duplicate message_id entries: {duplicates}", file=sys.stderr)
            return 1
        print("[PASS] Verified all message_id entries are unique")

        # 4. Check output.csv template schema
        output_path = resolve_dataset_path("output.csv")
        with open(output_path, mode="r", encoding="utf-8") as f:
            header_line = f.readline().strip()
            header_cols = header_line.split(",")
        validate_output_schema(header_cols)
        print("[PASS] Verified dataset/output.csv template schema")

        print("Phase 0 Diagnostic Check Completed Successfully. READY FOR PHASE 1.")
        return 0
    except Exception as exc:
        print(f"[FAIL] Diagnostic check failed: {exc}", file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Message Notification Router - Entry Point"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run Phase 0 diagnostic check on repository and dataset",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run the Phase 5 Hybrid Production Router Pipeline",
    )
    parser.add_argument(
        "--samples",
        action="store_true",
        help="Run the pipeline on sample_messages.csv instead of full messages.csv",
    )
    args = parser.parse_args()

    if args.run:
        print("Starting Production Pipeline...")
        run_pipeline(use_samples=args.samples)
        return 0

    if args.check or len(sys.argv) == 1:
        return run_diagnostic_check()

    return 0


if __name__ == "__main__":
    sys.exit(main())
