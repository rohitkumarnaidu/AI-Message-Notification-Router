import re
from datetime import datetime, timezone
from typing import Optional, List
from schemas import TemporalContext

# Fake urgency vs concrete deadlines
VAGUE_URGENCY_REGEX = re.compile(r'\b(urgent|immediately|asap|now|jaldi|turant|quick|hurry)\b', re.IGNORECASE)
CONCRETE_DEADLINE_REGEX = re.compile(r'\b(in \d+ (minutes|hours)|waiting outside|arriving|scheduled for|today at|tomorrow at)\b', re.IGNORECASE)

def extract_temporal_context(text: str, message_timestamp: str, user_timezone: str = "UTC") -> TemporalContext:
    ctx = TemporalContext(
        message_timestamp=message_timestamp,
        normalized_timezone=user_timezone
    )
    
    # Simple check for quiet hours (e.g. 10 PM to 7 AM local time)
    # Since we only have simple strings in the dataset, we'll do basic parsing if possible.
    try:
        dt = datetime.fromisoformat(message_timestamp.replace('Z', '+00:00'))
        hour = dt.hour
        # Default quiet hours: 22:00 to 07:00
        if hour >= 22 or hour < 7:
            ctx.is_quiet_hours = True
            ctx.quiet_hours_source = "default_22_to_07"
    except Exception:
        pass

    text_lower = text.lower()
    has_vague = bool(VAGUE_URGENCY_REGEX.search(text_lower))
    has_concrete = bool(CONCRETE_DEADLINE_REGEX.search(text_lower))
    
    if has_concrete:
        ctx.deadline_status = "future"
        ctx.temporal_phrases = CONCRETE_DEADLINE_REGEX.findall(text_lower)
    elif has_vague:
        ctx.temporal_phrases = VAGUE_URGENCY_REGEX.findall(text_lower)
        
    return ctx

def check_genuine_urgency(ctx: TemporalContext, text: str) -> bool:
    has_concrete = bool(CONCRETE_DEADLINE_REGEX.search(text))
    # Genuine urgency requires concrete deadlines, not just vague words.
    return has_concrete
