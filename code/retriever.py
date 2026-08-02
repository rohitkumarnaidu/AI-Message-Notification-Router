import re
from typing import List, Dict, Any, Set
from schemas import EvidenceCandidate, IncomingMessageContext
from datetime import datetime

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


def retrieve_evidence(msg_ctx: IncomingMessageContext, full_context: Dict[str, Any], max_evidence: int = 3, min_score_threshold: int = 3) -> List[EvidenceCandidate]:
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
        h_id = h.get("message_id", "")
        # Rule 15: Receiving-user isolation
        if h.get("user_id") != user_id or not user_id:
            continue
            
        # Rule 16: Temporal eligibility
        h_created = h.get("created_at", "")
        if created_at and h_created >= created_at:
            continue

        # Prevent leakage of prediction IDs (e.g. msg_...)
        if not h_id or h_id.startswith("msg_"):
            continue

        rel_type = "none"
        relationship_score = 0
        
        # Rule 17: Relationship-aware candidate generation
        if sender_id and h.get("sender_user_id") == sender_id:
            relationship_score += 3
            rel_type = "same_sender"
        elif business_id and h.get("business_id") == business_id:
            relationship_score += 3
            rel_type = "same_business"
            
        if group_id and h.get("group_id") == group_id and conv_type == "group":
            relationship_score += 2
            rel_type = "same_group" if rel_type == "none" else rel_type
            
        if conv_type and h.get("conversation_type") == conv_type:
            relationship_score += 1

        # Behavioral event matches
        ev = events_idx.get(h_id)
        behavioral_signal = "none"
        behavioral_score = 0
        if ev:
            if str(ev.get("message_reported", "")).strip().lower() in ("1", "true"):
                behavioral_score += 3
                behavioral_signal = "reported"
            elif str(ev.get("muted_after_message", "")).strip().lower() in ("1", "true"):
                behavioral_score += 2
                behavioral_signal = "muted"
            elif str(ev.get("notification_dismissed", "")).strip().lower() in ("1", "true"):
                behavioral_score += 1
                behavioral_signal = "dismissed"
            elif str(ev.get("message_replied", "")).strip().lower() in ("1", "true"):
                behavioral_score += 1
                behavioral_signal = "replied"

        # Content/Lexical overlap (+1 per shared token, max +2)
        h_tokens = _tokens(h.get("message_text", ""))
        lexical_score = min(2, len(msg_tokens.intersection(h_tokens)))

        # Rule 18: Relevance scoring
        total_score = relationship_score + behavioral_score + lexical_score
        
        # Rule 19: Evidence-threshold
        if total_score >= min_score_threshold:
            candidates.append(EvidenceCandidate(
                message_id=h_id,
                relationship_type=rel_type,
                behavioral_signal=behavioral_signal,
                timestamp=h_created,
                lexical_score=lexical_score,
                semantic_score=float(total_score), # Using semantic_score to store total_score temporarily
                recency_score=1.0,
                eligibility=True,
                exclusion_reason="",
            ))

    # Sort by overall score, then recency
    candidates.sort(
        key=lambda x: (x.semantic_score, x.timestamp), 
        reverse=True
    )

    # Rule 20: Evidence diversity and deduplication
    result: List[EvidenceCandidate] = []
    seen_ids: Set[str] = set()
    seen_rel_types: Set[str] = set()

    for c in candidates:
        if c.message_id in seen_ids:
            continue
            
        # Diversity check: limit 2 per relationship type unless high score
        if c.relationship_type in seen_rel_types and len([r for r in result if r.relationship_type == c.relationship_type]) >= 2:
            continue

        seen_ids.add(c.message_id)
        seen_rel_types.add(c.relationship_type)
        result.append(c)
        if len(result) >= max_evidence:
            break

    return result
