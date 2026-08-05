import csv
import json
from pathlib import Path

from loaders import load_full_dataset
from context_builder import build_message_context
from user_profile import build_user_profile
from retriever import retrieve_evidence
from media_processor import process_media
from router import route_message
from config import DATASET_DIR, OUTPUT_DIR
from schemas import OUTPUT_CSV_COLUMNS
from validators import validate_output_records, validate_row_count_and_ids

# We will patch provider.py dynamically so we don't hit the API
import provider
from schemas import RouterDecision

# Load previous outputs to serve as mock LLM responses
mock_cache = {}
try:
    with open(Path(OUTPUT_DIR) / "output.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mock_cache[row["message_id"]] = row
except Exception as e:
    print(f"Mock provider warning: {e}")

# We need a way to pass message_id to our mocked generate_routing_decision.
# We will use a global variable updated in our loop.
CURRENT_MESSAGE_ID = None

def mocked_generate_routing_decision(prompt: str, evidence_allowlist=None):
    if CURRENT_MESSAGE_ID in mock_cache:
        row = mock_cache[CURRENT_MESSAGE_ID]
        ev_ids = [e.strip() for e in row["evidence_message_ids"].split(";")] if row["evidence_message_ids"] and row["evidence_message_ids"] != "none" else ["none"]
        return RouterDecision(
            action=row["action"],
            message_type=row["message_type"],
            reason=row["reason"],
            confidence=float(row["confidence"]),
            evidence_message_ids=ev_ids
        )
    return RouterDecision(action="digest", message_type="unknown", reason="mock fallback", confidence=0.5, evidence_message_ids=["none"])

import router
router.generate_routing_decision = mocked_generate_routing_decision

def run_phase13():
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
        
        print(f"[{idx+1}] msg_ctx")
        msg_ctx = build_message_context(raw_msg, context, original_index=idx)
        print(f"[{idx+1}] user_prof")
        user_prof = build_user_profile(user_id, context)
        
        print(f"[{idx+1}] media")
        if media_id and media_type:
            from schemas import MediaAnalysis
            # Mock media analysis to prevent API hangs
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
                processor_version="mock"
            )
            
        print(f"[{idx+1}] retrieve_evidence")
        evidence = retrieve_evidence(msg_ctx, context)
        
        print(f"[{idx+1}] route_message")
        decision = route_message(msg_ctx, user_prof, evidence, raw_msg)
        
        print(f"[{idx+1}] done")
        
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
    
    out_path = Path(OUTPUT_DIR) / "phase13_interruption_candidate.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(output_records)
        
    print(f"Phase 13 output saved to {out_path}")

if __name__ == "__main__":
    run_phase13()
