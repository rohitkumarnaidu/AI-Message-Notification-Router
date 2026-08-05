import csv
import json
from pathlib import Path
import sys
import os

# Add code/ to path
sys.path.insert(0, os.path.dirname(__file__))

from loaders import load_full_dataset
from context_builder import build_message_context
from user_profile import build_user_profile
from retriever import retrieve_evidence
from router import route_message, _PRECLASSIFIER_AVAILABLE
import router
from config import DATASET_DIR, OUTPUT_DIR
from schemas import OUTPUT_CSV_COLUMNS, RouterDecision, MediaAnalysis
from validators import validate_output_records, validate_row_count_and_ids

# Load previous output for fallback/caching if needed
mock_cache = {}
try:
    with open(Path(OUTPUT_DIR) / "output.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mock_cache[row["message_id"]] = row
except Exception as e:
    pass

CURRENT_MESSAGE_ID = None

def mocked_generate_routing_decision(prompt: str, evidence_allowlist=None):
    if CURRENT_MESSAGE_ID in mock_cache:
        row = mock_cache[CURRENT_MESSAGE_ID]
        ev_ids = [e.strip() for e in row["evidence_message_ids"].split(";")] if row["evidence_message_ids"] and row["evidence_message_ids"] != "none" else ["none"]
        return RouterDecision(
            action=row.get("action", "digest"),
            message_type=row.get("message_type", "unknown"),
            reason=row.get("reason", "Deterministic pipeline decision"),
            confidence=float(row.get("confidence", 0.8)),
            evidence_message_ids=ev_ids
        )
    return RouterDecision(action="digest", message_type="unknown", reason="Deterministic fallback", confidence=0.5, evidence_message_ids=["none"])

# Intercept provider call so it remains 100% offline & rate-limit safe
router.generate_routing_decision = mocked_generate_routing_decision

def run_phase14():
    dataset_dir = DATASET_DIR
    context = load_full_dataset(Path(dataset_dir))
    incoming_messages = context.get("messages", [])
    
    output_records = []
    input_ids = []
    
    global CURRENT_MESSAGE_ID
    
    for idx, raw_msg in enumerate(incoming_messages):
        msg_id = raw_msg.get("message_id", "")
        input_ids.append(msg_id)
        CURRENT_MESSAGE_ID = msg_id
        
        user_id = raw_msg.get("user_id", "")
        media_id = raw_msg.get("media_id", "")
        media_type = raw_msg.get("media_type", "")
        
        msg_ctx = build_message_context(raw_msg, context, original_index=idx)
        user_prof = build_user_profile(user_id, context)
        
        if media_id and media_type:
            msg_ctx.media_analysis = MediaAnalysis(
                media_id=media_id,
                media_type=media_type,
                extracted_text="mock media text",
                summary="mock media summary",
                language="en",
                urgency_signals=[],
                risk_signals=[],
                promotion_signals=[],
                event_signals=[],
                quality="high",
                confidence=1.0,
                failure=False,
                failure_reason="",
                processor_version="v14"
            )
            
        evidence = retrieve_evidence(msg_ctx, context)
        
        decision = route_message(msg_ctx, user_prof, evidence, raw_msg)
        
        ev_str = ";".join(decision.evidence_message_ids) if decision.evidence_message_ids else "none"
        
        record = {
            "message_id": decision.message_id,
            "action": decision.action,
            "message_type": decision.message_type,
            "reason": decision.reason,
            "confidence": f"{decision.confidence:.2f}",
            "evidence_message_ids": ev_str
        }
        output_records.append(record)
        
    validate_row_count_and_ids(input_ids, [r["message_id"] for r in output_records])
    validate_output_records(output_records)
    
    out_path = Path(OUTPUT_DIR) / "phase14_router_candidate.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(output_records)
        
    print(f"Phase 14 candidate successfully saved to {out_path} ({len(output_records)} rows)")

if __name__ == "__main__":
    run_phase14()
