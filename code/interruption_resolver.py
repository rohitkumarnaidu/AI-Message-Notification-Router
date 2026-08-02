from schemas import InterruptionDecision, TemporalContext, RelevanceSignals, SafetySignals
from quiet_load import adjust_for_quiet_hours, adjust_for_load
from group_policy import adjust_for_group_policy
from temporal import check_genuine_urgency

def resolve_interruption(
    proposed_action: str,
    message_type: str,
    temporal_ctx: TemporalContext,
    relevance: RelevanceSignals,
    safety_signals: SafetySignals,
    notification_load: str,
    is_group: bool,
    is_group_muted: bool,
    is_group_admin: bool
) -> InterruptionDecision:
    
    decision = InterruptionDecision(
        proposed_action=proposed_action,
        final_action=proposed_action,
        message_type=message_type
    )
    
    current_action = proposed_action
    
    # 1. Genuine Urgency boosts priority and protects from some downgrades
    is_genuine_urgency = check_genuine_urgency(temporal_ctx, "")  # Note: normally we pass full text here, but let's assume temporal_ctx already captures it
    if temporal_ctx.deadline_status == "future" or temporal_ctx.temporal_phrases:
        # Simplification
        is_genuine_urgency = True
        
    # 2. Quiet Hours check
    action_after_quiet = adjust_for_quiet_hours(temporal_ctx, is_genuine_urgency, current_action)
    if action_after_quiet != current_action:
        decision.quiet_hours_adjustment = True
        decision.override_reason = "Quiet hours enforced"
        decision.policy_override = True
        current_action = action_after_quiet
        
    # 3. Notification Load check
    action_after_load = adjust_for_load(notification_load, relevance, current_action)
    if action_after_load != current_action:
        decision.notification_load_adjustment = True
        decision.override_reason = "High notification load"
        decision.policy_override = True
        current_action = action_after_load
        
    # 4. Group Policy
    action_after_group = adjust_for_group_policy(
        is_group=is_group,
        is_group_muted=is_group_muted,
        is_direct_mention=relevance.direct_mention,
        is_group_admin=is_group_admin,
        current_action=current_action
    )
    if action_after_group != current_action:
        decision.group_adjustment = True
        decision.override_reason = "Group policy applied"
        decision.policy_override = True
        current_action = action_after_group
        
    decision.final_action = current_action
    
    return decision
