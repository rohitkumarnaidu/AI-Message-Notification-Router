import re
from typing import Optional
from schemas import RelevanceSignals

def extract_relevance_signals(
    text: str,
    is_direct_message: bool = False,
    is_group_admin: bool = False,
    has_recent_engagement: bool = False
) -> RelevanceSignals:
    
    signals = RelevanceSignals(
        direct_message=is_direct_message,
        recent_engagement=has_recent_engagement
    )
    
    text_lower = text.lower()
    
    # Direct mention check
    if "@" in text or "hey everyone" not in text_lower:
        # Simple heuristic: if it has an @, it's a mention.
        if re.search(r'@[a-zA-Z0-9_]+', text):
            signals.direct_mention = True

    # Opt-in/Opt-out
    if re.search(r'\b(opt( |-)out|stop|unsubscribe)\b', text_lower):
        signals.user_opt_out = True
    if re.search(r'\b(opt( |-)in|subscribe)\b', text_lower):
        signals.user_opt_in = True
        
    # Transaction / Delivery
    if re.search(r'\b(order|delivery|package|arriving|shipped|tracking)\b', text_lower):
        signals.current_delivery = True
    if re.search(r'\b(payment|transaction|receipt|invoice)\b', text_lower):
        signals.current_transaction = True

    return signals
