import os
import csv
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

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

# Directories
CACHE_DIR = Path(".cache/phase8/enrichments")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

SCHEMA_VERSION = "1.0"

# Locks for writing to jsonl atomically
lock_text_ctx = threading.Lock()
lock_img_ctx = threading.Lock()
lock_aud_ctx = threading.Lock()
lock_route_ctx = threading.Lock()

def _write_jsonl(filepath: Path, record: dict, lock: threading.Lock):
    with lock:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

def _load_jsonl_dict(filepath: Path) -> dict:
    result = {}
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    rec = json.loads(line)
                    # Use only valid schema_version records
                    if rec.get("schema_version") == SCHEMA_VERSION:
                        result[rec["message_id"]] = rec
                except:
                    pass
    return result

def run_parallel_pipeline(dataset_dir: str = DATASET_DIR, output_dir: str = OUTPUT_DIR, use_samples: bool = False, subset_limit: int = 0):
    print(f"Loading dataset from: {dataset_dir}...")
    context = load_full_dataset(Path(dataset_dir))
    if use_samples:
        print("Using sample_messages.csv instead of full messages...")
        context["messages"] = load_csv_records(Path(dataset_dir) / "sample_messages.csv")
        
    incoming_messages = context.get("messages", [])
    if subset_limit > 0:
        incoming_messages = incoming_messages[:subset_limit]
        
    if not incoming_messages:
        print("No incoming messages found.")
        return
        
    print(f"Loaded {len(incoming_messages)} messages to process.")
    
    # Load versioned enrichment caches
    text_ctx_cache = _load_jsonl_dict(CACHE_DIR / "text_context.jsonl")
    img_ctx_cache = _load_jsonl_dict(CACHE_DIR / "image_analysis.jsonl")
    aud_ctx_cache = _load_jsonl_dict(CACHE_DIR / "audio_transcripts.jsonl")
    routing_cache = _load_jsonl_dict(CACHE_DIR / "routing_decision.jsonl")

    input_ids = [m.get("message_id") for m in incoming_messages]
    final_results = {}
    
    local_executor = ThreadPoolExecutor(max_workers=4)
    image_executor = ThreadPoolExecutor(max_workers=1)
    audio_executor = ThreadPoolExecutor(max_workers=2)
    routing_executor = ThreadPoolExecutor(max_workers=2)

    def process_lane_1_context(raw_msg, idx):
        msg_id = raw_msg.get("message_id", "")
        if msg_id in text_ctx_cache:
            return text_ctx_cache[msg_id]
        
        user_id = raw_msg.get("user_id", "")
        msg_ctx = build_message_context(raw_msg, context, original_index=idx)
        user_prof = build_user_profile(user_id, context)
        evidence = retrieve_evidence(msg_ctx, context)
        
        record = {
            "schema_version": SCHEMA_VERSION,
            "message_id": msg_id,
            "original_index": idx,
            "msg_ctx": msg_ctx.to_dict() if hasattr(msg_ctx, 'to_dict') else msg_ctx.__dict__,
            "user_prof": user_prof.to_dict() if hasattr(user_prof, 'to_dict') else user_prof.__dict__,
            "evidence": [e.to_dict() if hasattr(e, 'to_dict') else e.__dict__ for e in evidence]
        }
        
        _write_jsonl(CACHE_DIR / "text_context.jsonl", record, lock_text_ctx)
        return record

    def process_lane_2_image(raw_msg):
        msg_id = raw_msg.get("message_id", "")
        media_id = raw_msg.get("media_id", "")
        if not media_id or raw_msg.get("media_type") != "image":
            return None
            
        if msg_id in img_ctx_cache:
            return img_ctx_cache[msg_id]
            
        img_row = next((r for r in context.get("images", []) if r.get("image_id") == media_id), None)
        file_path = img_row.get("file_path") if img_row else ""
        
        analysis = process_media(media_id, "image", file_path)
        record = {
            "schema_version": SCHEMA_VERSION,
            "message_id": msg_id,
            "analysis": analysis.__dict__ if hasattr(analysis, '__dict__') else analysis
        }
        _write_jsonl(CACHE_DIR / "image_analysis.jsonl", record, lock_img_ctx)
        return record

    def process_lane_3_audio(raw_msg):
        msg_id = raw_msg.get("message_id", "")
        media_id = raw_msg.get("media_id", "")
        if not media_id or raw_msg.get("media_type") != "voice":
            return None
            
        if msg_id in aud_ctx_cache:
            return aud_ctx_cache[msg_id]
            
        vn_row = next((r for r in context.get("voice_notes", []) if r.get("voice_note_id") == media_id), None)
        file_path = vn_row.get("file_path") if vn_row else ""
        
        analysis = process_media(media_id, "voice", file_path)
        record = {
            "schema_version": SCHEMA_VERSION,
            "message_id": msg_id,
            "analysis": analysis.__dict__ if hasattr(analysis, '__dict__') else analysis
        }
        _write_jsonl(CACHE_DIR / "audio_transcripts.jsonl", record, lock_aud_ctx)
        return record

    def process_lane_4_routing(raw_msg, text_rec, img_rec, aud_rec):
        msg_id = raw_msg.get("message_id", "")
        if msg_id in routing_cache:
            return routing_cache[msg_id]["output_record"]
            
        idx = text_rec["original_index"]
        msg_ctx = build_message_context(raw_msg, context, original_index=idx)
        user_prof = build_user_profile(raw_msg.get("user_id", ""), context)
        evidence = retrieve_evidence(msg_ctx, context)
        
        if img_rec and img_rec.get("analysis"):
            from schemas import MediaAnalysis
            val = img_rec["analysis"]
            msg_ctx.media_analysis = MediaAnalysis(**val) if isinstance(val, dict) else val
        if aud_rec and aud_rec.get("analysis"):
            from schemas import MediaAnalysis
            val = aud_rec["analysis"]
            msg_ctx.media_analysis = MediaAnalysis(**val) if isinstance(val, dict) else val
            
        decision = route_message(msg_ctx, user_prof, evidence, raw_msg)
        validated_decision = validate_reason(decision)
        
        ev_str = ";".join(validated_decision.evidence_message_ids) if validated_decision.evidence_message_ids else "none"
        
        out_rec = {
            "message_id": validated_decision.message_id,
            "action": validated_decision.action,
            "message_type": validated_decision.message_type,
            "reason": validated_decision.reason,
            "confidence": f"{validated_decision.confidence:.2f}",
            "evidence_message_ids": ev_str
        }
        
        record = {
            "schema_version": SCHEMA_VERSION,
            "message_id": msg_id,
            "original_index": idx,
            "output_record": out_rec,
            "internal_trace": validated_decision.__dict__ if hasattr(validated_decision, '__dict__') else str(validated_decision)
        }
        _write_jsonl(CACHE_DIR / "routing_decision.jsonl", record, lock_route_ctx)
        return out_rec

    # Orchestrator
    print("Starting parallel processing...")
    
    futures = {}
    
    for idx, raw_msg in enumerate(incoming_messages):
        msg_id = raw_msg.get("message_id", "")
        
        # Dispatch lanes 1-3
        f_ctx = local_executor.submit(process_lane_1_context, raw_msg, idx)
        
        f_img = None
        if raw_msg.get("media_type") == "image":
            f_img = image_executor.submit(process_lane_2_image, raw_msg)
            
        f_aud = None
        if raw_msg.get("media_type") == "voice":
            f_aud = audio_executor.submit(process_lane_3_audio, raw_msg)
            
        # We need a routing future that waits on the dependencies
        def routing_task(rm=raw_msg, fc=f_ctx, fi=f_img, fa=f_aud):
            t_rec = fc.result()
            i_rec = fi.result() if fi else None
            a_rec = fa.result() if fa else None
            return process_lane_4_routing(rm, t_rec, i_rec, a_rec)
            
        f_route = routing_executor.submit(routing_task)
        futures[f_route] = msg_id

    completed = 0
    for f in as_completed(futures):
        msg_id = futures[f]
        try:
            res = f.result()
            final_results[msg_id] = res
            completed += 1
            if completed % 10 == 0 or completed == len(incoming_messages):
                print(f"Completed {completed}/{len(incoming_messages)}")
        except Exception as e:
            print(f"Error processing {msg_id}: {e}")

    # Shutdown
    local_executor.shutdown()
    image_executor.shutdown()
    audio_executor.shutdown()
    routing_executor.shutdown()
    
    # Sort by original input order
    output_records = []
    for m_id in input_ids:
        if m_id in final_results:
            output_records.append(final_results[m_id])
            
    # Validate
    out_ids = [r["message_id"] for r in output_records]
    validate_row_count_and_ids(input_ids, out_ids)
    validate_output_records(output_records)
    
    # Write Final Output
    out_path = Path(output_dir) / "phase8_parallel_candidate.csv"
    if use_samples:
        out_path = Path(output_dir) / "phase8_sample_candidate.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(output_records)
        
    print(f"Successfully processed {len(output_records)} messages.")
    print(f"Output saved to {out_path}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        run_parallel_pipeline(subset_limit=15)
    elif len(sys.argv) > 1 and sys.argv[1] == "sample":
        run_parallel_pipeline(use_samples=True)
    else:
        run_parallel_pipeline()
