import re
from typing import List, Dict, Any
from schemas import EvidenceCandidate, IncomingMessageContext

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


def retrieve_evidence(msg_ctx: IncomingMessageContext, full_context: Dict[str, Any], max_evidence: int = 3) -> List[EvidenceCandidate]:
    """Retrieve historical evidence returned as typed candidates."""
    
    user_id = msg_ctx.user_context.get("user_id", "")
    created_at = msg_ctx.timestamp
    sender_id = msg_ctx.sender_context.get("user_id", "")
    business_id = msg_ctx.business_context.get("business_id", "")
    group_id = msg_ctx.group_context.get("group_id", "")
    conv_type = msg_ctx.conversation_type
    msg_tokens = _tokens(msg_ctx.text)

    history = full_context.get("message_history", [])
    events_idx = {r["message_id"]: r for r in full_context.get("message_events", [])}

    candidates: List[EvidenceCandidate] = []

    for h in history:
        # Filter to same user_id
        if h.get("user_id") != user_id or not user_id:
            continue
            
        # Strict temporal order check
        h_created = h.get("created_at", "")
        if created_at and h_created >= created_at:
            continue

        h_id = h.get("message_id", "")
        # Prevent leakage of prediction IDs
        if not h_id or h_id.startswith("msg_"):
            continue

        rel_type = "none"
        score = 0
        
        # Sender / Business match (+3)
        if (sender_id and h.get("sender_user_id") == sender_id):
            score += 3
            rel_type = "same_sender"
        elif (business_id and h.get("business_id") == business_id):
            score += 3
            rel_type = "same_business"
            
        # Group match (+2)
        if group_id and h.get("group_id") == group_id and conv_type == "group":
            score += 2
            rel_type = "same_group" if rel_type == "none" else rel_type
            
        # Conversation type match (+1)
        if conv_type and h.get("conversation_type") == conv_type:
            score += 1

        # Behavioral event matches
        ev = events_idx.get(h_id)
        behavioral_signal = "none"
        if ev:
            if ev.get("message_reported", "").strip() in ("1", "true", "True"):
                score += 3
                behavioral_signal = "reported"
            elif ev.get("muted_after_message", "").strip() in ("1", "true", "True"):
                score += 2
                behavioral_signal = "muted"
            elif ev.get("notification_dismissed", "").strip() in ("1", "true", "True"):
                score += 1
                behavioral_signal = "dismissed"
            elif ev.get("message_replied", "").strip() in ("1", "true", "True"):
                score += 1
                behavioral_signal = "replied"

        # Token overlap (+1 per shared token, max +2)
        h_tokens = _tokens(h.get("message_text", ""))
        overlap = len(msg_tokens.intersection(h_tokens))
        score += min(2, overlap)

        if score > 0:
            candidates.append(EvidenceCandidate(
                message_id=h_id,
                relationship_type=rel_type,
                behavioral_signal=behavioral_signal,
                timestamp=h_created,
                lexical_score=overlap,
                semantic_score=0.0,
                recency_score=1.0,
                eligibility=True,
                exclusion_reason="",
            ))

    # Sort by overall score (sum of lexical, relational), then recency
    candidates.sort(
        key=lambda x: (
            x.lexical_score + (3 if x.relationship_type != 'none' else 0) + (2 if x.behavioral_signal != 'none' else 0), 
            x.timestamp
        ), 
        reverse=True
    )

    result = []
    seen = set()
    for c in candidates:
        if c.message_id not in seen:
            seen.add(c.message_id)
            result.append(c)
            if len(result) >= max_evidence:
                break

    return result
