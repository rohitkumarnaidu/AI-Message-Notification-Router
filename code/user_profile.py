from typing import List, Dict, Any
from schemas import UserProfile

def build_user_profile(user_id: str, context_indexes: Dict[str, Any]) -> UserProfile:
    """Build a typed UserProfile from the raw CSV indexes."""
    idx = context_indexes
    user_row = idx.get("users_idx", {}).get(user_id, {})
    
    # 1. Base User Metrics
    quiet_hours = user_row.get("dnd_window", "")
    try:
        opened = max(int(user_row.get("messages_opened_30d", 0) or 0), 1)
        replied = int(user_row.get("messages_replied_30d", 0) or 0)
        dismissed = int(user_row.get("notifications_dismissed_30d", 0) or 0)
        reported = int(user_row.get("messages_reported_30d", 0) or 0)
    except (ValueError, TypeError):
        opened, replied, dismissed, reported = 1, 0, 0, 0
        
    reply_patterns = replied / opened
    dismiss_patterns = dismissed / opened
    report_patterns = reported / opened
    notification_load = float(opened)

    # 2. Trusted Senders
    trusted_senders = []
    # Any sender replied to is considered trusted
    hist_rows = idx.get("hist_by_user", {}).get(user_id, [])
    for h in hist_rows:
        sender_id = h.get("sender_user_id")
        if not sender_id:
            continue
        ev = idx.get("events_idx", {}).get(h.get("message_id", ""))
        if ev and ev.get("message_replied", "").strip() in ("1", "true", "True"):
            if sender_id not in trusted_senders:
                trusted_senders.append(sender_id)

    # 3. Active / Muted Groups
    active_groups = []
    muted_groups = []
    for (uid, gid), gm_row in idx.get("gm_idx", {}).items():
        if uid == user_id:
            if gm_row.get("group_muted_by_user", "").strip() in ("1", "true", "True"):
                muted_groups.append(gid)
            else:
                active_groups.append(gid)

    # 4. Business Relationships
    business_opt_ins = []
    business_opt_outs = []
    recent_transactions = []
    for (uid, bid), ubh_row in idx.get("ubh_idx", {}).items():
        if uid == user_id:
            if ubh_row.get("opted_in", "").strip() in ("1", "true", "True"):
                business_opt_ins.append(bid)
            if ubh_row.get("opted_out", "").strip() in ("1", "true", "True"):
                business_opt_outs.append(bid)
            # check recent transaction
            if ubh_row.get("last_order_date") or ubh_row.get("last_booking_date") or ubh_row.get("last_payment_date"):
                recent_transactions.append(bid)

    history_strength = "strong" if len(hist_rows) > 5 else ("weak" if len(hist_rows) > 0 else "none")

    return UserProfile(
        user_id=user_id,
        quiet_hours=quiet_hours,
        notification_load=notification_load,
        trusted_senders=trusted_senders,
        active_groups=active_groups,
        muted_groups=muted_groups,
        business_opt_ins=business_opt_ins,
        business_opt_outs=business_opt_outs,
        recent_transactions=recent_transactions,
        reply_patterns=reply_patterns,
        dismiss_patterns=dismiss_patterns,
        report_patterns=report_patterns,
        history_strength=history_strength,
    )
