from schemas import TemporalContext, RelevanceSignals

def evaluate_notification_load(
    daily_notification_count: int,
    recent_notification_count: int
) -> str:
    # High load if user has received many notifications recently
    if daily_notification_count > 50 or recent_notification_count > 10:
        return "high"
    elif daily_notification_count < 5:
        return "low"
    return "normal"

def adjust_for_quiet_hours(
    temporal_ctx: TemporalContext, 
    is_genuine_urgency: bool,
    current_action: str
) -> str:
    if temporal_ctx.is_quiet_hours:
        # Genuine urgency overrides quiet hours
        if is_genuine_urgency:
            return current_action
        
        # If it's just a normal notify, downgrade to digest
        if current_action == "notify":
            return "digest"
            
    return current_action

def adjust_for_load(
    load_status: str,
    relevance: RelevanceSignals,
    current_action: str
) -> str:
    if load_status == "high" and current_action == "notify":
        # If it's a direct message or mention, let it through despite load
        if relevance.direct_message or relevance.direct_mention:
            return current_action
        # Otherwise downgrade to digest
        return "digest"
    return current_action
