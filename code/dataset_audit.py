"""
Phase 2 — Dataset Forensic Audit Script
Profiles every CSV and media file in dataset/ without modifying any official file.
Outputs machine-readable and human-readable reports to evidence/.
"""

import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = REPO_ROOT / "dataset"
EVIDENCE_DIR = REPO_ROOT / "evidence"
MEDIA_IMAGES_DIR = DATASET_DIR / "media" / "images"
MEDIA_AUDIO_DIR = DATASET_DIR / "media" / "audio"
EVIDENCE_DIR.mkdir(exist_ok=True)
GENERATED_AT = datetime.now().isoformat()

# ─── Helpers ─────────────────────────────────────────────────────────────────

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_csv(path: Path) -> tuple[list[str], list[dict]]:
    """Return (headers, rows) from a CSV. Raises on failure."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)
    return list(headers), rows


def count_missing(rows, col):
    return sum(1 for r in rows if not (r.get(col) or "").strip())


def count_dupes(rows, col):
    vals = [r.get(col, "") for r in rows if (r.get(col) or "").strip()]
    counts = Counter(vals)
    return [k for k, v in counts.items() if v > 1]


def enum_values(rows, col):
    return Counter((r.get(col) or "").strip() for r in rows)


# ─── PART 1: CSV File Inventory ───────────────────────────────────────────────

CSV_FILES = [
    "messages.csv",
    "sample_messages.csv",
    "users.csv",
    "groups.csv",
    "group_members.csv",
    "business_accounts.csv",
    "user_business_history.csv",
    "message_history.csv",
    "message_events.csv",
    "images.csv",
    "voice_notes.csv",
    "daily_notification_summary.csv",
    "output.csv",
]

csv_inventory = []
csv_data = {}

print("=== PHASE 2: DATASET FORENSIC AUDIT ===")
print(f"Generated: {GENERATED_AT}\n")
print("--- CSV File Inventory ---")

for fname in CSV_FILES:
    path = DATASET_DIR / fname
    entry = {
        "file": fname,
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else None,
        "sha256": None,
        "row_count": None,
        "col_count": None,
        "headers": None,
        "primary_key_candidate": None,
        "missing_per_col": {},
        "duplicate_ids": [],
        "read_error": None,
    }
    if path.exists():
        entry["sha256"] = sha256_file(path)
        try:
            headers, rows = load_csv(path)
            entry["row_count"] = len(rows)
            entry["col_count"] = len(headers)
            entry["headers"] = headers
            # Missing values per column
            for col in headers:
                missing = count_missing(rows, col)
                if missing:
                    entry["missing_per_col"][col] = missing
            csv_data[fname] = (headers, rows)
        except Exception as e:
            entry["read_error"] = str(e)
    csv_inventory.append(entry)
    status = "OK" if entry["exists"] and not entry["read_error"] else "ERROR"
    print(f"  {fname:40s} rows={entry['row_count'] or 'N/A':>6}  size={entry['size_bytes'] or 0:>10} B  [{status}]")

# ─── PART 2: Identifier & Duplicate Audit ─────────────────────────────────────

print("\n--- Identifier & Duplicate Audit ---")

ID_FIELDS = {
    "messages.csv": "message_id",
    "sample_messages.csv": "message_id",
    "users.csv": "user_id",
    "groups.csv": "group_id",
    "message_history.csv": "message_id",
    "images.csv": "image_id",
    "voice_notes.csv": "voice_note_id",
}

id_audit = {}
for fname, id_col in ID_FIELDS.items():
    if fname not in csv_data:
        continue
    headers, rows = csv_data[fname]
    dupes = count_dupes(rows, id_col)
    nulls = count_missing(rows, id_col)
    id_audit[fname] = {
        "id_col": id_col,
        "total": len(rows),
        "null_ids": nulls,
        "duplicate_ids": dupes,
    }
    print(f"  {fname:40s} id={id_col:20s} total={len(rows):>5}  nulls={nulls}  dupes={len(dupes)}")
    if dupes:
        print(f"    DUPLICATE IDs: {dupes[:10]}")

# ─── PART 3: Cross-File Relationship Validation ────────────────────────────────

print("\n--- Relationship Validation ---")

def fk_coverage(source_rows, fk_col, target_set, label=""):
    vals = [r.get(fk_col, "") for r in source_rows]
    valid = sum(1 for v in vals if v and v.strip() and v.strip() in target_set)
    missing = sum(1 for v in vals if not (v or "").strip())
    invalid = sum(1 for v in vals if (v or "").strip() and (v or "").strip() not in target_set)
    total = len(vals)
    print(f"  {label:55s} total={total:>5}  valid={valid:>5}  missing={missing:>5}  invalid={invalid:>5}")
    return {"total": total, "valid": valid, "missing": missing, "invalid_fk": invalid}

relationship_results = {}

# Build lookup sets
users_set = {r["user_id"] for r in csv_data["users.csv"][1]} if "users.csv" in csv_data else set()
groups_set = {r["group_id"] for r in csv_data["groups.csv"][1]} if "groups.csv" in csv_data else set()
businesses_set = {r["business_id"] for r in csv_data["business_accounts.csv"][1]} if "business_accounts.csv" in csv_data else set()
history_ids_set = {r["message_id"] for r in csv_data["message_history.csv"][1]} if "message_history.csv" in csv_data else set()
images_set = {r.get("image_id", r.get("id", "")) for r in csv_data["images.csv"][1]} if "images.csv" in csv_data else set()
voice_notes_set = {r.get("voice_note_id", r.get("id", "")) for r in csv_data["voice_notes.csv"][1]} if "voice_notes.csv" in csv_data else set()

if "messages.csv" in csv_data:
    _, msgs = csv_data["messages.csv"]

    # messages.user_id -> users
    relationship_results["msg->user"] = fk_coverage(msgs, "user_id", users_set, "messages.user_id -> users.user_id")

    # messages.group_id -> groups (only for group type)
    group_msgs = [r for r in msgs if r.get("conversation_type") == "group"]
    relationship_results["group_msg->group"] = fk_coverage(group_msgs, "group_id", groups_set, "group_msgs.group_id -> groups.group_id")

    # messages.business_id -> business (only for business type)
    biz_msgs = [r for r in msgs if r.get("conversation_type") == "business"]
    relationship_results["biz_msg->business"] = fk_coverage(biz_msgs, "business_id", businesses_set, "biz_msgs.business_id -> business_accounts.business_id")

    # messages.media_id for images
    img_msgs = [r for r in msgs if r.get("media_type") == "image"]
    relationship_results["img_msg->images"] = fk_coverage(img_msgs, "media_id", images_set, "img_msgs.media_id -> images.image_id")

    # messages.media_id for voice notes
    vn_msgs = [r for r in msgs if r.get("media_type") == "voice"]
    relationship_results["vn_msg->voicenotes"] = fk_coverage(vn_msgs, "media_id", voice_notes_set, "vn_msgs.media_id -> voice_notes.voice_note_id")

    # Check: users in messages not in users table
    unknown_users = [r["message_id"] for r in msgs if r.get("user_id") and r["user_id"] not in users_set]
    if unknown_users:
        print(f"  ORPHAN user_ids in messages (not in users.csv): {unknown_users[:5]}")

# message_events.message_id -> message_history
if "message_events.csv" in csv_data and "message_history.csv" in csv_data:
    _, events = csv_data["message_events.csv"]
    relationship_results["event->history"] = fk_coverage(events, "message_id", history_ids_set, "message_events.message_id -> message_history.message_id")

# ─── PART 4: Timestamp / Temporal Audit ───────────────────────────────────────

print("\n--- Timestamp Audit ---")

def parse_ts(ts_str):
    ts_str = (ts_str or "").strip()
    if not ts_str:
        return None
    formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]
    for fmt in formats:
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None

CURRENT_TS = datetime(2026, 8, 2)

def audit_timestamps(rows, col, label):
    parsed, missing, future = 0, 0, 0
    examples_future = []
    for r in rows:
        ts = parse_ts(r.get(col, ""))
        if ts is None:
            missing += 1
        else:
            parsed += 1
            if ts > CURRENT_TS:
                future += 1
                examples_future.append(str(ts))
    total = len(rows)
    print(f"  {label:50s} parsed={parsed}/{total}  missing={missing}  future={future}")
    return {"parsed": parsed, "total": total, "missing": missing, "future": future, "example_future": examples_future[:3]}

temporal_results = {}
if "messages.csv" in csv_data:
    _, msgs = csv_data["messages.csv"]
    temporal_results["messages"] = audit_timestamps(msgs, "created_at", "messages.created_at")
if "message_history.csv" in csv_data:
    _, hist = csv_data["message_history.csv"]
    temporal_results["message_history"] = audit_timestamps(hist, "created_at", "message_history.created_at")
if "message_events.csv" in csv_data:
    _, events = csv_data["message_events.csv"]
    for col in ["event_timestamp", "timestamp", "created_at"]:
        if col in (csv_data["message_events.csv"][0]):
            temporal_results["message_events"] = audit_timestamps(events, col, f"message_events.{col}")
            break

# ─── PART 5: Conversation Type Distribution ────────────────────────────────────

print("\n--- Conversation Type Distribution ---")
if "messages.csv" in csv_data:
    _, msgs = csv_data["messages.csv"]
    conv_type_dist = enum_values(msgs, "conversation_type")
    media_type_dist = enum_values(msgs, "media_type")
    fw_counts = [int(r.get("forwarded_count", 0) or 0) for r in msgs]
    print(f"  conversation_type: {dict(conv_type_dist)}")
    print(f"  media_type: {dict(media_type_dist)}")
    print(f"  forwarded_count: min={min(fw_counts)} max={max(fw_counts)} mean={sum(fw_counts)/len(fw_counts):.2f}")

# ─── PART 6: Solved Sample Distribution ───────────────────────────────────────

print("\n--- Solved Sample Distribution ---")
if "sample_messages.csv" in csv_data:
    _, samples = csv_data["sample_messages.csv"]
    action_dist = enum_values(samples, "action")
    mtype_dist = enum_values(samples, "message_type")
    media_dist = enum_values(samples, "media_type")
    conv_dist = enum_values(samples, "conversation_type")
    print(f"  Total solved samples: {len(samples)}")
    print(f"  action dist: {dict(action_dist)}")
    print(f"  message_type dist: {dict(mtype_dist)}")
    print(f"  media_type dist: {dict(media_dist)}")
    print(f"  conversation_type dist: {dict(conv_dist)}")

# ─── PART 7: Prompt Injection / Adversarial Patterns ─────────────────────────

print("\n--- Adversarial & Injection Pattern Scan ---")
INJECTION_PATTERNS = [
    (re.compile(r"ignore (all )?(previous |prior )?instructions", re.I), "prompt_injection"),
    (re.compile(r"(mark|set|label|classify|route) (this |it )?(as |to )?(notify|digest|mute)", re.I), "routing_override"),
    (re.compile(r"action\s*=\s*(notify|digest|mute)", re.I), "direct_label_injection"),
    (re.compile(r"(reveal|share|output|print) (system |your )?(prompt|instructions|policy)", re.I), "prompt_extraction"),
    (re.compile(r"(change|override|switch) (your )?(role|behavior|mode)", re.I), "role_override"),
    (re.compile(r"\b(OTP|otp)\b.*\b(share|send|enter|confirm|verify)\b", re.I), "otp_request"),
    (re.compile(r"\b(password|passwd|pin)\b.*(share|send|enter|confirm)", re.I), "credential_request"),
    (re.compile(r"(account.will.be.block|profile.will.be.block|access.will.be.suspend)", re.I), "account_block_threat"),
    (re.compile(r"(account-login|account-help|chase-secure|pay-check-secure|amazonpay-delivery|bit\.ly)", re.I), "suspicious_link"),
    (re.compile(r"scan (this |the )?QR.*(pay|send|submit)", re.I), "qr_payment_pressure"),
    (re.compile(r"(share|send|fill).*(bank detail|account number|card detail)", re.I), "financial_data_request"),
    (re.compile(r"(forward|share) (to |with |this in |in all).*(group|family|everyone)", re.I), "chain_forward"),
    (re.compile(r"(claim|won|selected|reward|voucher|prize).*(today|now|quickly|fast|hurry)", re.I), "lottery_claim"),
]

adversarial_findings = []
if "messages.csv" in csv_data:
    _, msgs = csv_data["messages.csv"]
    for r in msgs:
        text = (r.get("message_text") or "").strip()
        if not text:
            continue
        for pattern, category in INJECTION_PATTERNS:
            if pattern.search(text):
                adversarial_findings.append({
                    "message_id": r["message_id"],
                    "category": category,
                    "text_preview": text[:80].replace("\n", " "),
                })
    # deduplicate same message / same category
    seen = set()
    unique_findings = []
    for f in adversarial_findings:
        key = (f["message_id"], f["category"])
        if key not in seen:
            seen.add(key)
            unique_findings.append(f)
    adversarial_findings = unique_findings

print(f"  Total adversarial findings: {len(adversarial_findings)}")
cat_counts = Counter(f["category"] for f in adversarial_findings)
for cat, cnt in sorted(cat_counts.items()):
    print(f"    {cat:35s}: {cnt}")

# ─── PART 8: Media File Inventory ─────────────────────────────────────────────

print("\n--- Media File Inventory ---")
image_files = sorted(MEDIA_IMAGES_DIR.glob("*.jpg")) + sorted(MEDIA_IMAGES_DIR.glob("*.png"))
audio_files = sorted(MEDIA_AUDIO_DIR.glob("*.mp3")) + sorted(MEDIA_AUDIO_DIR.glob("*.ogg"))

print(f"  Image files on disk: {len(image_files)}")
for f in image_files:
    print(f"    {f.name:20s}  {f.stat().st_size:>10} B")

print(f"  Audio files on disk: {len(audio_files)}")
for f in audio_files:
    print(f"    {f.name:20s}  {f.stat().st_size:>10} B")

# Check referenced media vs on-disk
if "images.csv" in csv_data:
    _, img_rows = csv_data["images.csv"]
    imgs_headers, _ = csv_data["images.csv"]
    file_col = "file_path" if "file_path" in imgs_headers else "image_path" if "image_path" in imgs_headers else imgs_headers[-1]
    img_id_col = "image_id" if "image_id" in imgs_headers else imgs_headers[0]
    print(f"\n  images.csv columns: {imgs_headers}")
    on_disk_names = {f.name for f in image_files}
    for r in img_rows:
        ref_path = (r.get(file_col) or "").strip()
        fname_only = Path(ref_path).name if ref_path else ""
        exists = fname_only in on_disk_names
        if not exists:
            print(f"    MISSING image: {ref_path}")

if "voice_notes.csv" in csv_data:
    _, vn_rows = csv_data["voice_notes.csv"]
    vn_headers, _ = csv_data["voice_notes.csv"]
    vn_file_col = "file_path" if "file_path" in vn_headers else vn_headers[-1]
    vn_id_col = "voice_note_id" if "voice_note_id" in vn_headers else vn_headers[0]
    print(f"\n  voice_notes.csv columns: {vn_headers}")
    on_disk_audio_names = {f.name for f in audio_files}
    for r in vn_rows:
        ref_path = (r.get(vn_file_col) or "").strip()
        fname_only = Path(ref_path).name if ref_path else ""
        exists = fname_only in on_disk_audio_names
        if not exists:
            print(f"    MISSING voice note: {ref_path}")

# ─── PART 9: Language Profile ─────────────────────────────────────────────────

print("\n--- Language/Text Profile ---")
if "messages.csv" in csv_data:
    _, msgs = csv_data["messages.csv"]
    texts = [r.get("message_text", "") or "" for r in msgs]
    has_hindi = sum(1 for t in texts if re.search(r'[\u0900-\u097F]', t))
    has_emoji = sum(1 for t in texts if re.search(r'[\U0001F300-\U0001FAD6]', t))
    has_url = sum(1 for t in texts if re.search(r'https?://|bit\.ly|\.in/|\.com/', t))
    has_otp_pattern = sum(1 for t in texts if re.search(r'\b(OTP|otp|one.time|login.code|verification.code)\b', t))
    empty_text = sum(1 for t in texts if not t.strip())
    lengths = [len(t) for t in texts if t.strip()]
    print(f"  Total messages: {len(msgs)}")
    print(f"  Empty text (media-only): {empty_text}")
    print(f"  Contains Devanagari script: {has_hindi}")
    print(f"  Contains emoji: {has_emoji}")
    print(f"  Contains URL/link: {has_url}")
    print(f"  Contains OTP pattern: {has_otp_pattern}")
    if lengths:
        print(f"  Text length: min={min(lengths)} max={max(lengths)} mean={sum(lengths)/len(lengths):.0f} chars")

# ─── PART 10: Users Personalization Overview ──────────────────────────────────

print("\n--- Users Personalization Overview ---")
if "users.csv" in csv_data:
    u_headers, users = csv_data["users.csv"]
    print(f"  users.csv columns: {u_headers}")
    print(f"  Total users: {len(users)}")
    for col in u_headers:
        miss = count_missing(users, col)
        if miss:
            print(f"    Missing '{col}': {miss}/{len(users)}")

if "group_members.csv" in csv_data:
    gm_headers, gm = csv_data["group_members.csv"]
    print(f"\n  group_members.csv columns: {gm_headers}")
    print(f"  Total group_member rows: {len(gm)}")
    if "muted" in gm_headers or "is_muted" in gm_headers:
        mute_col = "muted" if "muted" in gm_headers else "is_muted"
        muted_dist = enum_values(gm, mute_col)
        print(f"  muted distribution: {dict(muted_dist)}")

# ─── PART 11: Row-Order Audit ─────────────────────────────────────────────────

print("\n--- Row Order Audit ---")
if "messages.csv" in csv_data:
    _, msgs = csv_data["messages.csv"]
    msg_ids = [r["message_id"] for r in msgs]
    unique_ids = set(msg_ids)
    print(f"  Total rows: {len(msg_ids)}")
    print(f"  Unique message_ids: {len(unique_ids)}")
    print(f"  Duplicates: {len(msg_ids) - len(unique_ids)}")

# ─── SAVE RESULTS ─────────────────────────────────────────────────────────────

results = {
    "generated_at": GENERATED_AT,
    "csv_inventory": csv_inventory,
    "id_audit": id_audit,
    "relationship_results": relationship_results,
    "temporal_results": temporal_results,
    "adversarial_findings": adversarial_findings,
    "media_image_count": len(image_files),
    "media_audio_count": len(audio_files),
}

output_path = EVIDENCE_DIR / "dataset_audit_results.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, default=str)

print(f"\n✓ Audit complete. Results saved to {output_path}")
print("═" * 60)
