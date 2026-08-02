"""
Deterministic feature extraction for Message Notification Router baseline_v1.

Extracts Boolean and numeric features from:
- Message text (regex patterns)
- Structured context (users, groups, business accounts, history, events)

No message IDs are hardcoded. All patterns are generalizable.
Media files are confirmed for existence only — no OCR or ASR is performed.
"""

import re
import unicodedata
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Text normalisation helpers
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    """Lowercase, Unicode-normalise, collapse whitespace. Preserve numbers/URLs."""
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _extract_urls(text: str) -> list[str]:
    """Extract all URL-like strings from text."""
    return re.findall(r"https?://[^\s]+|www\.[^\s]+|[a-z0-9.-]+\.[a-z]{2,}/[^\s]*", text.lower())


# Domains considered trusted for business messages (expand as evidence grows)
_TRUSTED_DOMAINS = frozenset([
    "amazon.in", "amazon.com", "flipkart.com", "myntra.com", "zomato.com",
    "swiggy.com", "ola.in", "uber.com", "paytm.com", "phonepe.com",
    "hdfcbank.com", "sbi.co.in", "icicibank.com", "axisbank.com",
    "irctc.co.in", "pvrinemas.com", "bookmyshow.com", "redbus.in",
    "makemytrip.com", "cleartrip.com", "goibibo.com", "airtel.in",
    "jio.com", "bsnl.co.in", "vodafone.in", "google.com", "microsoft.com",
])

_SUSPICIOUS_LINK_PATTERNS = re.compile(
    r"account-login|account-help|verify-|secure-|pay-check|-rewards|"
    r"bit\.ly|tinyurl|shorte\.st|is\.gd|ow\.ly|goo\.gl|t\.co/[a-z0-9]{3,}|"
    r"login-verify|otp-confirm|wallet-verify|profile-update-[a-z]",
    re.IGNORECASE,
)

_STOPWORDS = frozenset([
    "the", "and", "for", "that", "this", "with", "have", "from", "your",
    "been", "will", "they", "what", "when", "were", "their", "there",
    "which", "about", "into", "than", "then", "some", "also", "just",
    "please", "here", "more", "only", "any", "can", "are", "not", "our",
    "you", "has", "all", "but", "its", "may", "over", "now", "get",
])

# ---------------------------------------------------------------------------
# Text feature patterns
# ---------------------------------------------------------------------------

_OTP_REQUEST = re.compile(
    r"\b(otp|one.time.pass(?:word|code)?|verification.code|login.code)\b.{0,30}"
    r"(share|send|enter|reply|submit|confirm)",
    re.IGNORECASE | re.DOTALL,
)

_CREDENTIAL_REQUEST = re.compile(
    r"(password|passwd|\bpin\b|login.code|account.code).{0,30}"
    r"(share|send|give|enter|confirm|reply)",
    re.IGNORECASE | re.DOTALL,
)

_PAYMENT_PRESSURE = re.compile(
    r"(scan.{0,10}qr|pay.{0,15}(?:now|immediately|today|urgent|fast)|"
    r"clearance.amount|token.amount|advance.payment)",
    re.IGNORECASE | re.DOTALL,
)

_ACCOUNT_BLOCK_THREAT = re.compile(
    r"(account|profile|access).{0,20}"
    r"(block|restrict|suspend|deactivat|terminat|lock).{0,30}"
    r"(hour|minute|today|now|immediately|unless|or.else)",
    re.IGNORECASE | re.DOTALL,
)

_LOTTERY_CLAIM = re.compile(
    r"(won|selected|congratulation|winner|claim.{0,10}(?:prize|reward|voucher|gift)).{0,30}"
    r"(now|today|quickly|fast|hurry|immediately)",
    re.IGNORECASE | re.DOTALL,
)

_PROMPT_INJECTION = re.compile(
    r"(ignore.{0,15}(?:previous|prior|all|routing|instructions)|"
    r"mark.{0,10}(?:this|message).{0,10}(?:as|to).{0,5}(?:notify|digest|mute)|"
    r"action\s*=\s*(?:notify|digest|mute)|"
    r"system.note.for.{0,10}router|internal.router|routing.override|"
    r"assistant.instruction|system:\s*override|new.system.prompt)",
    re.IGNORECASE | re.DOTALL,
)

_FORWARD_LANGUAGE = re.compile(
    r"(fwd\b|forwarded|forward as received|share this|please forward|"
    r"pls forward|forward to all|sharing here|sharing with you|as received)",
    re.IGNORECASE,
)

_PROMOTION_LANGUAGE = re.compile(
    r"(%\s*off|discount|deal|special offer|\boffer\b|\bsale\b|cashback|"
    r"coupon|\bpromo\b|voucher|subscribe|unsubscribe|reply stop|tap below|"
    r"valid today|limited time|exclusive)",
    re.IGNORECASE,
)

_GREETING_START = re.compile(
    r"^(good morning|good evening|good afternoon|good night|"
    r"hey everyone|hello everyone|greetings|happy \w+|blessed|wishing)",
    re.IGNORECASE,
)

_EVENT_DATE = re.compile(
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"today|tomorrow|this week|next week|"
    r"\d{1,2}[/-]\d{1,2}|\d{1,2}\s*(?:jan|feb|mar|apr|may|jun|"
    r"jul|aug|sep|oct|nov|dec))\b",
    re.IGNORECASE,
)

_IMMEDIATE_TIME = re.compile(
    r"\b(now|immediately|right now|urgent|asap|"
    r"in \d+\s*min(?:ute)?s?|within \d+\s*min(?:ute)?s?|"
    r"before \d+:\d+|leaving in|waiting|on the way|"
    r"\d+\s*mins?\s*left|\d+\s*hours?\s*left|minutes? max)\b",
    re.IGNORECASE,
)

_DEADLINE = re.compile(
    r"(before \d|by \d|closed?\s*(?:at|by)|due\s*(?:at|by)|"
    r"\beod\b|end of day|expires?\s*(?:today|soon|at)|last chance|\bdeadline\b|"
    r"pls.{0,15}before|reply.{0,15}before)",
    re.IGNORECASE | re.DOTALL,
)

_WAITING_SIGNAL = re.compile(
    r"(tanker|bus|driver|delivery|order|package|courier).{0,40}"
    r"(wait(?:ing)?|leaving|arrived|here|at.gate|at.door|outside|ready|at.stop)",
    re.IGNORECASE | re.DOTALL,
)

_QR_REFERENCE = re.compile(
    r"(qr.?code|scan.{0,10}qr|qr.{0,10}scan|payment qr)",
    re.IGNORECASE,
)

_FINANCIAL_DATA = re.compile(
    r"(bank.detail|account.number|card.detail|\bcvv\b|routing.number|"
    r"sort.code|ifsc|swift.code)",
    re.IGNORECASE,
)

_DIRECT_MENTION = re.compile(r"@(u_\d+)", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Timestamp parsing
# ---------------------------------------------------------------------------

_DT_FORMATS = ["%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]


def _parse_dt(val: str) -> datetime | None:
    if not val:
        return None
    for fmt in _DT_FORMATS:
        try:
            return datetime.strptime(val.strip(), fmt)
        except ValueError:
            continue
    return None


def _is_quiet_hour(created_at_str: str, dnd_window: str) -> bool:
    """Return True if created_at falls within the DND window (HH:MM-HH:MM)."""
    if not dnd_window or not created_at_str:
        return False
    try:
        msg_dt = _parse_dt(created_at_str)
        if not msg_dt:
            return False
        parts = dnd_window.strip().split("-")
        if len(parts) != 2:
            return False
        start_h, start_m = map(int, parts[0].strip().split(":"))
        end_h, end_m = map(int, parts[1].strip().split(":"))
        msg_time = msg_dt.hour * 60 + msg_dt.minute
        start = start_h * 60 + start_m
        end = end_h * 60 + end_m
        if start <= end:
            return start <= msg_time <= end
        else:  # cross-midnight window
            return msg_time >= start or msg_time <= end
    except Exception:
        return False


def _within_days(date_str: str, reference_str: str, days: int = 30) -> bool:
    """Return True if date_str is non-empty and within `days` days before reference_str."""
    ref_dt = _parse_dt(reference_str)
    target_dt = _parse_dt(date_str)
    if not ref_dt or not target_dt:
        return False
    return 0 <= (ref_dt - target_dt).days <= days


# ---------------------------------------------------------------------------
# Context index builders (called once per batch)
# ---------------------------------------------------------------------------

def _build_context_indexes(context: dict) -> dict:
    """
    Pre-build lookup dictionaries for efficient per-row access.
    Returns a dict of indexed structures.
    """
    # users: {user_id -> row}
    users_idx = {r["user_id"]: r for r in context.get("users", [])}

    # groups: {group_id -> row}
    groups_idx = {r["group_id"]: r for r in context.get("groups", [])}

    # group_members: {(user_id, group_id) -> row}
    gm_idx: dict[tuple, dict] = {}
    for r in context.get("group_members", []):
        gm_idx[(r["user_id"], r["group_id"])] = r

    # group_members by group_id: {group_id -> list of rows} (for admin lookup)
    gm_by_group: dict[str, list] = {}
    for r in context.get("group_members", []):
        gm_by_group.setdefault(r["group_id"], []).append(r)

    # business_accounts: {business_id -> row}
    biz_idx = {r["business_id"]: r for r in context.get("business_accounts", [])}

    # user_business_history: {(user_id, business_id) -> row}
    ubh_idx: dict[tuple, dict] = {}
    for r in context.get("user_business_history", []):
        ubh_idx[(r["user_id"], r["business_id"])] = r

    # message_history: list (filtered per message in extract_features)
    # Pre-index by user_id for efficiency
    hist_by_user: dict[str, list] = {}
    for r in context.get("message_history", []):
        hist_by_user.setdefault(r["user_id"], []).append(r)

    # message_events: {message_id -> row}
    events_idx = {r["message_id"]: r for r in context.get("message_events", [])}

    # images: {image_id -> file_path}
    images_idx = {r.get("image_id", r.get("media_id", "")): r.get("file_path", "") for r in context.get("images", [])}

    # voice_notes: {voice_note_id -> file_path}
    vn_idx = {r.get("voice_note_id", r.get("media_id", "")): r.get("file_path", "") for r in context.get("voice_notes", [])}

    return {
        "users_idx": users_idx,
        "groups_idx": groups_idx,
        "gm_idx": gm_idx,
        "gm_by_group": gm_by_group,
        "biz_idx": biz_idx,
        "ubh_idx": ubh_idx,
        "hist_by_user": hist_by_user,
        "events_idx": events_idx,
        "images_idx": images_idx,
        "vn_idx": vn_idx,
    }


# Module-level cache for indexes (rebuilt when context changes)
_cached_context_id: int | None = None
_cached_indexes: dict = {}


def _get_indexes(context: dict) -> dict:
    global _cached_context_id, _cached_indexes
    ctx_id = id(context)
    if ctx_id != _cached_context_id:
        _cached_indexes = _build_context_indexes(context)
        _cached_context_id = ctx_id
    return _cached_indexes


# ---------------------------------------------------------------------------
# Main feature extraction function
# ---------------------------------------------------------------------------

def extract_features(msg: dict, context: dict) -> dict:
    """
    Extract deterministic features from a single message row and its context.
    """
    idx = _get_indexes(context)

    user_id = msg.get("user_id", "")
    group_id = msg.get("group_id", "")
    business_id = msg.get("business_id", "")
    sender_id = msg.get("sender_user_id", "")
    conv_type = msg.get("conversation_type", "")
    created_at = msg.get("created_at", "")
    raw_text = msg.get("message_text", "") or ""
    media_type = msg.get("media_type", "") or ""
    media_id = msg.get("media_id", "") or ""
    try:
        forwarded_count = int(msg.get("forwarded_count", 0) or 0)
    except (ValueError, TypeError):
        forwarded_count = 0

    text = _normalise(raw_text)

    # 1. Text features
    contains_otp_request = bool(_OTP_REQUEST.search(text))
    contains_credential_request = bool(_CREDENTIAL_REQUEST.search(text))
    contains_payment_pressure = bool(_PAYMENT_PRESSURE.search(text))
    contains_account_block_threat = bool(_ACCOUNT_BLOCK_THREAT.search(text))
    contains_lottery_claim = bool(_LOTTERY_CLAIM.search(text))
    contains_prompt_injection = bool(_PROMPT_INJECTION.search(text))
    contains_forward_language = bool(_FORWARD_LANGUAGE.search(text))
    contains_promotion_language = bool(_PROMOTION_LANGUAGE.search(text))
    contains_greeting = bool(_GREETING_START.search(text))
    contains_event_date = bool(_EVENT_DATE.search(text))
    contains_immediate_time_reference = bool(_IMMEDIATE_TIME.search(text))
    contains_deadline = bool(_DEADLINE.search(text))
    contains_waiting_signal = bool(_WAITING_SIGNAL.search(text))
    contains_qr_reference = bool(_QR_REFERENCE.search(text))
    contains_financial_data_request = bool(_FINANCIAL_DATA.search(text))

    # Direct mention — check for @user_id in text
    mentioned_ids = _DIRECT_MENTION.findall(raw_text)
    contains_direct_mention = user_id in [f"u_{m}" if not m.startswith("u_") else m
                                           for m in mentioned_ids]
    if not contains_direct_mention and conv_type == "personal":
        contains_direct_mention = bool(
            re.search(r"\byou\b", text) and (contains_deadline or contains_immediate_time_reference)
        )

    # Suspicious link detection
    urls = _extract_urls(raw_text)
    contains_suspicious_link = False
    for url in urls:
        if _SUSPICIOUS_LINK_PATTERNS.search(url):
            contains_suspicious_link = True
            break
        domain_match = re.search(r"(?:https?://|www\.)([a-z0-9.-]+)", url)
        if domain_match:
            domain = domain_match.group(1).lstrip("www.")
            if not any(domain.endswith(td) for td in _TRUSTED_DOMAINS):
                if re.search(r"verify|account|login|secure|otp|wallet|pay", url):
                    contains_suspicious_link = True
                    break

    # 2. Forwarding signal
    high_forward_count = forwarded_count >= 5

    # 3. Sender / group / business structured signals
    sender_is_group_admin = False
    if conv_type == "group" and group_id and sender_id:
        gm_row = idx["gm_idx"].get((sender_id, group_id))
        if gm_row and gm_row.get("role", "").lower() == "admin":
            sender_is_group_admin = True

    group_is_muted = False
    if conv_type == "group" and group_id and user_id:
        gm_row = idx["gm_idx"].get((user_id, group_id))
        if gm_row and gm_row.get("group_muted_by_user", "").strip() in ("1", "true", "True"):
            group_is_muted = True

    business_is_verified = False
    domain_mismatch = False
    business_reports_high = False
    if conv_type == "business" and business_id:
        biz_row = idx["biz_idx"].get(business_id)
        if biz_row:
            business_is_verified = biz_row.get("verified", "").strip() in ("1", "true", "True")
            official_domain = biz_row.get("official_domain", "").strip().lower()
            sender_domain = biz_row.get("domain_used_by_sender", "").strip().lower()
            if official_domain and sender_domain and official_domain != sender_domain:
                domain_mismatch = True
            try:
                business_reports_high = int(biz_row.get("user_reports_30d", 0) or 0) > 20
            except (ValueError, TypeError):
                business_reports_high = False

    user_opted_in = False
    user_opted_out = False
    user_has_active_transaction = False
    if conv_type == "business" and business_id and user_id:
        ubh_row = idx["ubh_idx"].get((user_id, business_id))
        if ubh_row:
            user_opted_in = ubh_row.get("opted_in", "").strip() in ("1", "true", "True")
            user_opted_out = ubh_row.get("opted_out", "").strip() in ("1", "true", "True")
            for date_field in ("last_order_date", "last_booking_date", "last_payment_date"):
                if _within_days(ubh_row.get(date_field, ""), created_at, days=30):
                    user_has_active_transaction = True
                    break

    # 4. User signals
    user_engagement_rate = 0.0
    user_dismiss_rate = 0.0
    user_report_count = 0
    quiet_hours_active = False
    context_missing = False

    user_row = idx["users_idx"].get(user_id)
    if user_row:
        try:
            opened = max(int(user_row.get("messages_opened_30d", 0) or 0), 1)
            replied = int(user_row.get("messages_replied_30d", 0) or 0)
            dismissed = int(user_row.get("notifications_dismissed_30d", 0) or 0)
            reported = int(user_row.get("messages_reported_30d", 0) or 0)
            user_engagement_rate = replied / opened
            user_dismiss_rate = dismissed / opened
            user_report_count = reported
        except (ValueError, TypeError):
            pass
        dnd_window = user_row.get("dnd_window", "") or ""
        quiet_hours_active = _is_quiet_hour(created_at, dnd_window)
    else:
        context_missing = True

    if conv_type == "group" and group_id and not idx["gm_idx"].get((user_id, group_id)):
        context_missing = True

    # 5. Historical behavioral signals
    hist_rows = idx["hist_by_user"].get(user_id, [])
    relevant_hist: list[dict] = []
    for h in hist_rows:
        h_created = h.get("created_at", "")
        if created_at and h_created >= created_at:
            continue
        if (h.get("sender_user_id") == sender_id and sender_id) or \
           (h.get("group_id") == group_id and group_id) or \
           (h.get("business_id") == business_id and business_id):
            relevant_hist.append(h)

    historical_reply_signal = False
    historical_dismiss_signal = False
    historical_report_signal = False
    historical_mute_signal = False

    for h in relevant_hist:
        ev = idx["events_idx"].get(h.get("message_id", ""))
        if ev:
            if ev.get("message_replied", "").strip() in ("1", "true", "True"):
                historical_reply_signal = True
            if ev.get("notification_dismissed", "").strip() in ("1", "true", "True"):
                historical_dismiss_signal = True
            if ev.get("message_reported", "").strip() in ("1", "true", "True"):
                historical_report_signal = True
            if ev.get("muted_after_message", "").strip() in ("1", "true", "True"):
                historical_mute_signal = True

    sender_is_known = len(relevant_hist) > 0
    sender_trusted_personal = (
        conv_type == "personal" and sender_is_known and historical_reply_signal
    )

    # 6. Media signals
    media_present = bool(media_type)
    media_available = False
    if media_present and media_id:
        if media_type in ("image", "photo"):
            file_path = idx["images_idx"].get(media_id, "")
        elif media_type in ("voice", "audio", "voice_note"):
            file_path = idx["vn_idx"].get(media_id, "")
        else:
            file_path = ""
        if file_path:
            repo_root = Path(__file__).resolve().parent.parent
            media_available = (repo_root / file_path).exists()

    return {
        "contains_otp_request": contains_otp_request,
        "contains_credential_request": contains_credential_request,
        "contains_payment_pressure": contains_payment_pressure,
        "contains_account_block_threat": contains_account_block_threat,
        "contains_lottery_claim": contains_lottery_claim,
        "contains_prompt_injection": contains_prompt_injection,
        "contains_forward_language": contains_forward_language,
        "contains_promotion_language": contains_promotion_language,
        "contains_greeting": contains_greeting,
        "contains_event_date": contains_event_date,
        "contains_immediate_time_reference": contains_immediate_time_reference,
        "contains_deadline": contains_deadline,
        "contains_waiting_signal": contains_waiting_signal,
        "contains_qr_reference": contains_qr_reference,
        "contains_financial_data_request": contains_financial_data_request,
        "contains_direct_mention": contains_direct_mention,
        "contains_suspicious_link": contains_suspicious_link,
        "high_forward_count": high_forward_count,
        "forwarded_count": forwarded_count,
        "sender_is_group_admin": sender_is_group_admin,
        "group_is_muted": group_is_muted,
        "business_is_verified": business_is_verified,
        "domain_mismatch": domain_mismatch,
        "business_reports_high": business_reports_high,
        "user_opted_in": user_opted_in,
        "user_opted_out": user_opted_out,
        "user_has_active_transaction": user_has_active_transaction,
        "historical_reply_signal": historical_reply_signal,
        "historical_dismiss_signal": historical_dismiss_signal,
        "historical_report_signal": historical_report_signal,
        "historical_mute_signal": historical_mute_signal,
        "sender_is_known": sender_is_known,
        "sender_trusted_personal": sender_trusted_personal,
        "user_engagement_rate": user_engagement_rate,
        "user_dismiss_rate": user_dismiss_rate,
        "user_report_count": user_report_count,
        "quiet_hours_active": quiet_hours_active,
        "context_missing": context_missing,
        "media_present": media_present,
        "media_available": media_available,
    }
