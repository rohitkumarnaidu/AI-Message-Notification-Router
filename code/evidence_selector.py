"""
Deterministic historical evidence selector for Message Notification Router baseline_v1.
Selects up to `max_evidence` relevant message IDs from message_history based on sender, group,
behavioral events, and token overlap. Never leaks future timestamps or incoming message IDs.
"""

import re

_STOPWORDS = frozenset([
    "the", "and", "for", "that", "this", "with", "have", "from", "your",
    "been", "will", "they", "what", "when", "were", "their", "there",
    "which", "about", "into", "than", "then", "some", "also", "just",
    "please", "here", "more", "only", "any", "can", "are", "not", "our",
    "you", "has", "all", "but", "its", "may", "over", "now", "get",
])


def _tokens(text: str) -> set[str]:
    if not text:
        return set()
    words = re.findall(r"\b[a-z0-9]{4,}\b", text.lower())
    return set(words) - _STOPWORDS


def select_evidence(msg: dict, context: dict, max_evidence: int = 3) -> list[str]:
    """
    Select up to `max_evidence` relevant historical message_ids for `msg`.
    
    Returns a list of string message_ids (format 'message_0XXX').
    If no valid candidates exist, returns an empty list [].
    """
    user_id = msg.get("user_id", "")
    created_at = msg.get("created_at", "")
    sender_id = msg.get("sender_user_id", "")
    business_id = msg.get("business_id", "")
    group_id = msg.get("group_id", "")
    conv_type = msg.get("conversation_type", "")
    msg_tokens = _tokens(msg.get("message_text", ""))

    history = context.get("message_history", [])
    events_idx = {r["message_id"]: r for r in context.get("message_events", [])}

    candidates = []

    for h in history:
        # Filter to same user_id
        if h.get("user_id") != user_id or not user_id:
            continue
        # Strict temporal order check: history created_at must be < incoming created_at
        h_created = h.get("created_at", "")
        if created_at and h_created >= created_at:
            continue

        h_id = h.get("message_id", "")
        # Must be historical message format (message_0XXX), never incoming msg_* format
        if not h_id or h_id.startswith("msg_"):
            continue

        score = 0
        # Sender / Business match (+3)
        if (sender_id and h.get("sender_user_id") == sender_id) or (
            business_id and h.get("business_id") == business_id
        ):
            score += 3
        # Group match (+2)
        if group_id and h.get("group_id") == group_id and conv_type == "group":
            score += 2
        # Conversation type match (+1)
        if conv_type and h.get("conversation_type") == conv_type:
            score += 1

        # Behavioral event matches
        ev = events_idx.get(h_id)
        if ev:
            if ev.get("message_reported", "").strip() in ("1", "true", "True"):
                score += 3
            if ev.get("muted_after_message", "").strip() in ("1", "true", "True"):
                score += 2
            if ev.get("notification_dismissed", "").strip() in ("1", "true", "True"):
                score += 1
            if ev.get("message_replied", "").strip() in ("1", "true", "True"):
                score += 1

        # Token overlap (+1 per shared token, max +2)
        h_tokens = _tokens(h.get("message_text", ""))
        overlap = len(msg_tokens.intersection(h_tokens))
        score += min(2, overlap)

        if score > 0:
            candidates.append((score, h_created, h_id))

    # Sort by score descending, then by created_at descending (recency)
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

    result = []
    seen = set()
    for _, _, h_id in candidates:
        if h_id not in seen:
            seen.add(h_id)
            result.append(h_id)
            if len(result) >= max_evidence:
                break

    return result
