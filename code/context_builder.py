from typing import Dict, Any, List
from schemas import IncomingMessageContext
from feature_extractor import extract_features, _get_indexes

def build_message_context(
    message_row: Dict[str, Any], 
    full_context_dataset: Dict[str, Any],
    original_index: int
) -> IncomingMessageContext:
    """Build the typed IncomingMessageContext ensuring no cross-user leakage."""
    
    msg_id = message_row.get("message_id", "")
    user_id = message_row.get("user_id", "")
    
    # Run the deterministic baseline feature extraction which also handles
    # missing context detection, safety signals, and urgency features.
    deterministic_signals = extract_features(message_row, full_context_dataset)
    
    # Re-use the indexes built in feature_extractor for fast lookup
    idx = _get_indexes(full_context_dataset)
    
    # User Context
    user_context = idx.get("users_idx", {}).get(user_id, {})
    
    # Sender Context
    sender_id = message_row.get("sender_user_id", "")
    sender_context = idx.get("users_idx", {}).get(sender_id, {}) if sender_id else {}
    
    # Group Context
    group_id = message_row.get("group_id", "")
    group_context = idx.get("groups_idx", {}).get(group_id, {}) if group_id else {}
    
    # Business Context
    business_id = message_row.get("business_id", "")
    business_context = idx.get("biz_idx", {}).get(business_id, {}) if business_id else {}
    
    # Missing Context
    missing_context = []
    if not user_context:
        missing_context.append("user_profile")
    if group_id and not idx.get("gm_idx", {}).get((user_id, group_id)):
        missing_context.append("group_membership")
        
    return IncomingMessageContext(
        message_id=msg_id,
        original_index=original_index,
        timestamp=message_row.get("created_at", ""),
        conversation_type=message_row.get("conversation_type", ""),
        text=message_row.get("message_text", "") or "",
        media_type=message_row.get("media_type", "") or "",
        media_id=message_row.get("media_id", "") or "",
        user_context=user_context,
        sender_context=sender_context,
        group_context=group_context,
        business_context=business_context,
        historical_context={}, # Filtered out by retriever explicitly
        deterministic_signals=deterministic_signals,
        missing_context=missing_context,
    )
