import json
from typing import Dict, Any, List
from schemas import IncomingMessageContext, RouterDecision, EvidenceCandidate, FinalDecision
from provider import generate_routing_decision, ProviderFallbackError, PolicyRejectionError
from baseline_policy import route as baseline_route

def build_llm_prompt(msg_ctx: IncomingMessageContext, profile: Any, evidence: List[EvidenceCandidate]) -> str:
    """Builds the prompt string combining all contexts."""
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


def get_human_readable_reason(rule_id: str, action: str, msg_type: str) -> str:
    """Map internal baseline rule IDs to grounded, concise, human-readable final reasons."""
    reasons = {
        "prompt_injection_detected": "Message exhibits adversarial routing manipulation or system prompt injection.",
        "otp_scam": "Suspicious request for an OTP or verification code from an untrusted source.",
        "credential_request": "Suspicious request for passwords or account credentials from an untrusted source.",
        "account_block_scam": "Threat of account restriction combined with unverified sender credentials.",
        "qr_payment_scam": "Unverified request to scan a QR code for immediate payment.",
        "lottery_scam": "Message claims a lottery or prize reward from an unverified source.",
        "domain_mismatch_scam": "Sender domain does not match the official business domain for a highly reported account.",
        "financial_data_scam": "Suspicious request for sensitive financial details from an untrusted source.",
        "repeated_forward_muted": "Frequently forwarded message matching a history of muted interactions.",
        "repeated_forward_dismissed": "Frequently forwarded message matching a history of dismissed notifications.",
        "opted_out_promotion": "Promotional content from a business that the user has explicitly opted out of.",
        "user_muted_similar": "Matches a strong historical pattern of muted messages from this sender.",
        "admin_operational_urgent": "Time-sensitive operational update from a recognized group admin.",
        "trusted_sender_deadline": "Time-sensitive event or deadline from a trusted sender or admin.",
        "verified_business_active_transaction": "Relevant update regarding an active transaction with a verified business.",
        "direct_mention_urgent": "Direct personal mention requiring immediate attention.",
        "trusted_personal_urgent": "Urgent personal message from a trusted sender.",
        "waiting_signal_trusted": "Time-sensitive arrival or waiting status from a recognized contact.",
        "report_and_dismiss_history": "Sender has a consistent history of being reported and dismissed.",
        "opted_in_business_promo": "Promotional content from a verified business the user is subscribed to.",
        "explicit_opt_in_promo": "Explicitly requested promotional content.",
        "future_event": "Information regarding a future event that does not require immediate action.",
        "verified_business_non_urgent": "Routine business update that does not require immediate action.",
        "harmless_greeting": "Standard greeting that does not contain urgent information.",
        "dismiss_history_non_urgent": "Non-urgent message matching a pattern of previously dismissed notifications.",
        "known_sender_safe": "Standard personal message from a known contact without urgent deadlines.",
        "default_conservative": "Message lacks clear urgency or personal relevance, safely routed to digest."
    }
    return reasons.get(rule_id, f"Routed to {action} based on structural patterns and sender history.")


def route_message(msg_ctx: IncomingMessageContext, profile: Any, evidence: List[EvidenceCandidate], raw_message: dict) -> FinalDecision:
    """
    Main routing pipeline implementing selective_hybrid_v1:
    1. Check Deterministic-only cases (Safety, strong history, explicit opt-out).
    2. Try LLM Provider for ambiguous or complex cases.
    3. Fallback to Baseline Deterministic Policy on provider error or policy rejection.
    4. Apply Hard Policy Overrides.
    """
    overrides = []
    
    # 1. Evaluate baseline rules
    baseline_res = baseline_route(msg_ctx.deterministic_signals, raw_message)
    triggered_rules = baseline_res.get("triggered_rules", [])
    primary_rule = triggered_rules[0] if triggered_rules else "default_conservative"
    
    # Define rules that completely bypass the LLM (Selective Hybrid escalation)
    deterministic_bypass_rules = {
        "prompt_injection_detected", "otp_scam", "credential_request", 
        "account_block_scam", "qr_payment_scam", "lottery_scam", 
        "domain_mismatch_scam", "financial_data_scam", 
        "opted_out_promotion", "harmless_greeting", 
        "report_and_dismiss_history", "repeated_forward_muted"
    }

    if primary_rule in deterministic_bypass_rules:
        # Fast-path: bypass LLM
        action = baseline_res.get("action", "digest")
        msg_type = baseline_res.get("message_type", "unknown")
        reason = get_human_readable_reason(primary_rule, action, msg_type)
        conf = float(baseline_res.get("confidence", 0.8))
        ev_ids = [e.message_id for e in evidence[:3]]
    else:
        # 2. Model-escalated cases
        try:
            prompt = build_llm_prompt(msg_ctx, profile, evidence)
            valid_evidence_ids = [e.message_id for e in evidence]
            llm_decision = generate_routing_decision(prompt, evidence_allowlist=valid_evidence_ids)
            
            action = llm_decision.action
            msg_type = llm_decision.message_type
            reason = llm_decision.reason
            conf = llm_decision.confidence
            ev_ids = llm_decision.evidence_message_ids
            
            # Penalize confidence if media was present but unavailable
            if msg_ctx.deterministic_signals.get("media_present") and not msg_ctx.deterministic_signals.get("media_available"):
                conf -= 0.1
                
        except PolicyRejectionError as e:
            # 3a. Policy Rejection Fallback (Safety overrides without re-prompting)
            overrides.append("policy_rejection_fallback")
            action = "mute" if msg_ctx.deterministic_signals.get("media_present") else "digest"
            msg_type = "spam" if action == "mute" else "unknown"
            reason = "Content flagged by provider safety policies; safely routed to prevent exposure."
            conf = 0.5  # low confidence because we couldn't properly analyze
            ev_ids = [ev.message_id for ev in evidence[:3]]
            
        except ProviderFallbackError:
            # 3b. Graceful Deterministic Fallback on API / Quota failure
            overrides.append("llm_fallback_to_baseline")
            action = baseline_res.get("action", "digest")
            msg_type = baseline_res.get("message_type", "unknown")
            reason = get_human_readable_reason(primary_rule, action, msg_type)
            # Penalize confidence for falling back on a complex case
            conf = max(0.4, float(baseline_res.get("confidence", 0.6)) - 0.1)
            ev_ids = [e.message_id for e in evidence[:3]]

    # 4. Hard Safety / Overrides Policy
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
        
    # Ensure confidence limits and prevent automatic 1.0
    conf = max(0.0, min(0.99, conf))

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
