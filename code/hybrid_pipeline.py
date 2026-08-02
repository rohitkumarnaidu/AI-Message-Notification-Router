import csv
import sys
from pathlib import Path

# Local application imports
from loaders import load_full_dataset, load_csv_records
from context_builder import build_message_context
from user_profile import build_user_profile
from retriever import retrieve_evidence
from media_processor import process_media
from router import route_message
from reason_validator import validate_reason
from config import DATASET_DIR, OUTPUT_DIR
from schemas import OUTPUT_CSV_COLUMNS
from validators import validate_output_records, validate_row_count_and_ids

def run_pipeline(dataset_dir: str = DATASET_DIR, output_dir: str = OUTPUT_DIR, use_samples: bool = False):
    """
    Execute the hybrid router pipeline over the incoming messages.
    """
    
    print(f"Loading dataset from: {dataset_dir}...")
    context = load_full_dataset(Path(dataset_dir))
    if use_samples:
        print("Using sample_messages.csv instead of full messages...")
        context["messages"] = load_csv_records(Path(dataset_dir) / "sample_messages.csv")
        
    incoming_messages = context.get("messages", [])
    
    if not incoming_messages:
        print("No incoming messages found.")
        return
        
    print(f"Loaded {len(incoming_messages)} messages to process.")
    
    output_records = []
    input_ids = []
    
    # Process messages strictly in sequence to guarantee original ordering
    for idx, raw_msg in enumerate(incoming_messages):
        msg_id = raw_msg.get("message_id", "")
        input_ids.append(msg_id)
        user_id = raw_msg.get("user_id", "")
        media_id = raw_msg.get("media_id", "")
        media_type = raw_msg.get("media_type", "")
        
        print(f"[{idx+1}/{len(incoming_messages)}] Processing {msg_id} (media: {bool(media_id)})")
        
        # 1. Build typed structures
        msg_ctx = build_message_context(raw_msg, context, original_index=idx)
        user_prof = build_user_profile(user_id, context)
        
        # 2. Process Media if available
        if media_id and media_type:
            # We assume images and voice_notes dicts map media_id -> file_path
            # The media processor fetches this.
            img_row = next((r for r in context.get("images", []) if r.get("image_id") == media_id), None)
            vn_row = next((r for r in context.get("voice_notes", []) if r.get("voice_note_id") == media_id), None)
            file_path = img_row.get("file_path") if img_row else (vn_row.get("file_path") if vn_row else "")
            
            media_analysis = process_media(media_id, media_type, file_path)
            msg_ctx.media_analysis = media_analysis
            
        # 3. Retrieve Evidence
        evidence = retrieve_evidence(msg_ctx, context)
        
        # 4. Hybrid LLM + Deterministic Router
        decision = route_message(msg_ctx, user_prof, evidence, raw_msg)
        
        # 5. Output Validation
        validated_decision = validate_reason(decision)
        
        # Prepare for CSV
        ev_str = ";".join(validated_decision.evidence_message_ids) if validated_decision.evidence_message_ids else "none"
        
        record = {
            "message_id": validated_decision.message_id,
            "action": validated_decision.action,
            "message_type": validated_decision.message_type,
            "reason": validated_decision.reason,
            "confidence": f"{validated_decision.confidence:.2f}",
            "evidence_message_ids": ev_str
        }
        output_records.append(record)
        
    # Final architectural validations
    output_ids = [r["message_id"] for r in output_records]
    validate_row_count_and_ids(input_ids, output_ids)
    validate_output_records(output_records)
    
    # Write Output
    out_path = Path(output_dir) / "output.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(output_records)
        
    print(f"Successfully processed {len(output_records)} messages.")
    print(f"Output saved to {out_path}")

if __name__ == "__main__":
    run_pipeline()
