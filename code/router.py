import json
from typing import Dict, Any, List
from schemas import IncomingMessageContext, RouterDecision, EvidenceCandidate, FinalDecision
from provider import generate_structured_decision, ProviderFallbackError
from baseline_policy import route as baseline_route

def build_llm_prompt(msg_ctx: IncomingMessageContext, profile: Any, evidence: List[EvidenceCandidate]) -> str:
    """Builds the prompt string combining all contexts."""
    
    # We serialize the context safely
    ctx_dict = {
        "message": {
            "text": msg_ctx.text,
            "conversation_type": msg_ctx.conversation_type,
            "has_media": bool(msg_ctx.media_type)
        },
        "user_profile": {
            "quiet_hours": profile.quiet_hours,
            "notification_load": profile.notification_load,
            "trusted_senders_count": len(profile.trusted_senders)
        },
        "evidence": [
            {
                "id": ev.message_id,
                "relationship": ev.relationship_type,
                "behavior": ev.behavioral_signal
            } for ev in evidence
        ],
        "signals": msg_ctx.deterministic_signals
    }
    
    return f"Evaluate the following message context and determine the notification action (notify, digest, mute):\n\n{json.dumps(ctx_dict, indent=2)}"


def route_message(msg_ctx: IncomingMessageContext, profile: Any, evidence: List[EvidenceCandidate], raw_message: dict) -> FinalDecision:
    """
    Main routing pipeline:
    1. Try LLM Provider
    2. Fallback to Baseline Deterministic Policy on failure
    3. Apply Hard Policy Overrides
    """
    
    overrides = []
    
    try:
        prompt = build_llm_prompt(msg_ctx, profile, evidence)
        llm_decision = generate_structured_decision(prompt)
        
        # If we got here, we have a valid LLM decision
        action = llm_decision.action
        msg_type = llm_decision.message_type
        reason = llm_decision.reason
        conf = llm_decision.confidence
        ev_ids = llm_decision.evidence_message_ids
        
    except ProviderFallbackError:
        # Graceful Deterministic Fallback
        overrides.append("llm_fallback_to_baseline")
        
        baseline_res = baseline_route(msg_ctx.deterministic_signals, raw_message)
        
        action = baseline_res.get("action", "digest")
        msg_type = baseline_res.get("message_type", "unknown")
        reason = f"Baseline Fallback Rules: {', '.join(baseline_res.get('triggered_rules', []))}"
        conf = float(baseline_res.get("confidence", 0.6))
        
        # Select top evidence ID based on the candidates we generated
        ev_ids = [e.message_id for e in evidence[:3]]

    # Hard Safety / Overrides Policy (Step 3 in Phase 5 plan)
    # Never override Scam -> notify.
    if msg_ctx.deterministic_signals.get("contains_prompt_injection"):
        if action != "mute":
            overrides.append("safety_override_prompt_injection")
            action = "mute"
            msg_type = "scam"
            
    # If the LLM somehow chooses notify for a scam or spam, override
    if msg_type in ("scam", "spam") and action == "notify":
        overrides.append(f"safety_override_{msg_type}_downgrade")
        action = "mute"
        
    # Quiet hours policy downgrade
    if msg_ctx.deterministic_signals.get("quiet_hours_active") and action == "notify" and msg_type not in ("urgent", "event"):
        overrides.append("policy_override_quiet_hours_downgrade")
        action = "digest"
        
    # Ensure confidence limits
    conf = max(0.0, min(1.0, conf))

    return FinalDecision(
        message_id=msg_ctx.message_id,
        original_index=msg_ctx.original_index,
        action=action,
        message_type=msg_type,
        reason=reason,
        confidence=conf,
        evidence_message_ids=ev_ids,
        policy_overrides=overrides,
        validation_status="valid"
    )
