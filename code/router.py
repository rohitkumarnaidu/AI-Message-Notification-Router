import json
from typing import Dict, Any, List, Optional
from schemas import (
    IncomingMessageContext, RouterDecision, EvidenceCandidate, FinalDecision,
    SafetySignals
)
from provider import generate_routing_decision, ProviderFallbackError, PolicyRejectionError
from baseline_policy import route as baseline_route

# Phase 12 safety pipeline
try:
    from safety_detectors import extract_safety_signals
    from safety_policy import resolve_policy
    from unsafe_notify_validator import prevent_unsafe_notify, audit_final_output, reset_stats
    _SAFETY_PIPELINE_AVAILABLE = True
except ImportError:
    _SAFETY_PIPELINE_AVAILABLE = False

# Phase 13 interruption policy pipeline
try:
    from temporal import extract_temporal_context
    from relevance import extract_relevance_signals
    from quiet_load import evaluate_notification_load
    from interruption_resolver import resolve_interruption
    _INTERRUPTION_PIPELINE_AVAILABLE = True
except ImportError:
    _INTERRUPTION_PIPELINE_AVAILABLE = False

def build_llm_prompt(msg_ctx: IncomingMessageContext, profile: Any, evidence: List[EvidenceCandidate]) -> str:
    """Builds the prompt string combining all contexts."""
    media_data = {}
    if msg_ctx.media_analysis:
        media_data = {
            "type": msg_ctx.media_analysis.media_type,
            "extracted_text": msg_ctx.media_analysis.extracted_text,
            "visual_summary": msg_ctx.media_analysis.summary,
            "urgency_signals": msg_ctx.media_analysis.urgency_signals,
            "risk_signals": msg_ctx.media_analysis.risk_signals,
            "promotion_signals": msg_ctx.media_analysis.promotion_signals
        }
        if hasattr(msg_ctx.media_analysis, "has_qr_code"):
            media_data["has_qr_code"] = msg_ctx.media_analysis.has_qr_code
            media_data["has_financial_elements"] = msg_ctx.media_analysis.has_financial_elements
            media_data["has_promotional_elements"] = msg_ctx.media_analysis.has_promotional_elements

    ctx_dict = {
        "message": {
            "text": msg_ctx.text,
            "conversation_type": msg_ctx.conversation_type,
            "has_media": bool(msg_ctx.media_type),
            "media_analysis": media_data
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
    Main routing pipeline — Phase 12 selective_hybrid_v2:
    0. Extract Phase 12 SafetySignals (deterministic).
    1. Check deterministic bypass rules (safety, history, opt-out).
    2. Try provider for genuinely ambiguous cases (subordinate to safety).
    3. Fallback to baseline on provider error.
    4. Apply Phase 12 policy resolver (10-level priority).
    5. Apply unsafe-notify validator.
    """
    overrides = []

    # Phase 12: Extract safety signals from all sources
    safety_signals = None
    if _SAFETY_PIPELINE_AVAILABLE:
        try:
            safety_signals = extract_safety_signals(
                msg_ctx, raw_message, profile,
                all_message_ids=None,  # validated upstream
                event_ids=set(),
                evidence_timestamps={},
            )
        except Exception:
            safety_signals = None  # graceful degradation, existing policy continues
    
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
        if not ev_ids:
            ev_ids = ["none"]
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
            if not ev_ids:
                ev_ids = ["none"]
            elif len(ev_ids) == 1 and ev_ids[0].lower() == "none":
                ev_ids = ["none"]
            
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
            ev_ids = [e.message_id for e in evidence[:3]]
            if not ev_ids:
                ev_ids = ["none"]
            
        except ProviderFallbackError:
            # 3b. Graceful Deterministic Fallback on API / Quota failure
            overrides.append("llm_fallback_to_baseline")
            action = baseline_res.get("action", "digest")
            msg_type = baseline_res.get("message_type", "unknown")
            reason = get_human_readable_reason(primary_rule, action, msg_type)
            # Penalize confidence for falling back on a complex case
            conf = max(0.4, float(baseline_res.get("confidence", 0.6)) - 0.1)
            ev_ids = [e.message_id for e in evidence[:3]]
            if not ev_ids:
                ev_ids = ["none"]

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
        
    # 5. Image Processing overrides
    if msg_ctx.media_type == "image" and msg_ctx.media_analysis:
        if getattr(msg_ctx.media_analysis, 'is_prompt_injection', False):
            overrides.append("safety_override_image_prompt_injection")
            action = "mute"
            msg_type = "scam"
            
        # Conflict: Text is harmless, but image has risk signals
        if action in ("notify", "digest") and ("scam" in msg_ctx.media_analysis.risk_signals or getattr(msg_ctx.media_analysis, 'has_financial_elements', False) and not msg_ctx.deterministic_signals.get("sender_trusted_personal")):
            overrides.append("safety_override_image_risk")
            action = "mute"
            msg_type = "scam"
            conf -= 0.2
            
        # Conflict: Promo elements visually detected despite innocuous text
        if action == "notify" and getattr(msg_ctx.media_analysis, 'has_promotional_elements', False) and not msg_ctx.deterministic_signals.get("user_opted_in"):
            overrides.append("digest_override_image_promo")
            action = "digest"
            msg_type = "promotion"
            
        # Image failure/fallback penalty
        if getattr(msg_ctx.media_analysis, 'failure', False):
            conf -= 0.15
            
        # If it's a known sender and they send a pure image without text, give it some baseline confidence boost
        if msg_ctx.conversation_type == "personal" and not msg_ctx.text.strip():
            if msg_ctx.deterministic_signals.get("sender_trusted_personal"):
                action = "notify"
                msg_type = "personal"
                overrides.append("notify_trusted_personal_image")
                
    # 6. Voice Processing overrides
    if msg_ctx.media_type == "voice" and msg_ctx.media_analysis:
        if getattr(msg_ctx.media_analysis, 'is_prompt_injection', False):
            overrides.append("safety_override_voice_prompt_injection")
            action = "mute"
            msg_type = "scam"
            
        # Conflict: Text is harmless, but voice has risk signals
        if action in ("notify", "digest") and ("scam" in msg_ctx.media_analysis.risk_signals or getattr(msg_ctx.media_analysis, 'has_financial_elements', False) and not msg_ctx.deterministic_signals.get("sender_trusted_personal")):
            overrides.append("safety_override_voice_risk")
            action = "mute"
            msg_type = "scam"
            conf -= 0.2
            
        # Conflict: Promo elements detected in voice despite innocuous text
        if action == "notify" and getattr(msg_ctx.media_analysis, 'has_promotional_elements', False) and not msg_ctx.deterministic_signals.get("user_opted_in"):
            overrides.append("digest_override_voice_promo")
            action = "digest"
            msg_type = "promotion"
            
        # Voice failure/fallback penalty
        if getattr(msg_ctx.media_analysis, 'failure', False):
            conf -= 0.15
            
    # Ensure confidence limits and prevent automatic 1.0
    conf = max(0.0, min(0.99, conf))
    
    # Rule 21: Reason-to-evidence consistency
    if ev_ids == ["none"] and ("history" in reason.lower() or "previously" in reason.lower()):
        overrides.append("evidence_consistency_correction")
        reason = "Routed based on structural patterns and sender information without specific historical evidence."

    # ----------------------------------------------------------------
    # Phase 12: Policy Resolver (10-level priority chain)
    # ----------------------------------------------------------------
    if _SAFETY_PIPELINE_AVAILABLE and safety_signals is not None:
        try:
            media_quality = getattr(
                msg_ctx.media_analysis, 'quality', 'none'
            ) if msg_ctx.media_analysis else 'none'
            if msg_ctx.media_analysis and getattr(msg_ctx.media_analysis, 'failure', False):
                media_quality = 'failed'

            policy_decision, policy_reason = resolve_policy(
                proposed_action=action,
                proposed_type=msg_type,
                proposed_reason=reason,
                proposed_confidence=conf,
                proposed_evidence_ids=ev_ids,
                safety_signals=safety_signals,
                deterministic_signals=msg_ctx.deterministic_signals,
                media_quality=media_quality,
                evidence_quality='none',
            )

            if policy_decision.override_applied:
                overrides.append(f"phase12_policy_{policy_decision.override_reason_code}")

            action = policy_decision.final_action
            msg_type = policy_decision.final_message_type
            reason = policy_reason
            ev_ids = policy_decision.allowed_evidence_ids
            conf = max(policy_decision.confidence_floor,
                       min(policy_decision.confidence_ceiling, conf))

        except Exception:
            pass  # graceful degradation — existing overrides already applied

    # ----------------------------------------------------------------
    # Phase 13: Interruption Policy Resolver
    # ----------------------------------------------------------------
    if _INTERRUPTION_PIPELINE_AVAILABLE:
        try:
            # Reconstruct Phase 13 Contexts
            temporal_ctx = extract_temporal_context(
                text=msg_ctx.text, 
                message_timestamp=getattr(msg_ctx, "timestamp", "2026-08-01T12:00:00Z"),
                user_timezone=getattr(profile, "timezone", "UTC")
            )
            
            relevance_signals = extract_relevance_signals(
                text=msg_ctx.text,
                is_direct_message=(msg_ctx.conversation_type == "personal"),
                is_group_admin=msg_ctx.deterministic_signals.get("is_admin", False),
                has_recent_engagement=msg_ctx.deterministic_signals.get("recent_engagement", False)
            )
            
            notification_load = evaluate_notification_load(
                daily_notification_count=getattr(profile, "daily_notifications", 0),
                recent_notification_count=getattr(profile, "recent_notifications", 0)
            )
            
            decision = resolve_interruption(
                proposed_action=action,
                message_type=msg_type,
                temporal_ctx=temporal_ctx,
                relevance=relevance_signals,
                safety_signals=safety_signals,
                notification_load=notification_load,
                is_group=(msg_ctx.conversation_type == "group"),
                is_group_muted=getattr(profile, "group_muted", False),
                is_group_admin=msg_ctx.deterministic_signals.get("is_admin", False)
            )
            
            if decision.policy_override:
                overrides.append(f"phase13_interruption_{decision.override_reason.replace(' ', '_')}")
                action = decision.final_action
                reason = f"{decision.override_reason}: {reason}"
                
        except Exception:
            pass # graceful degradation

    # ----------------------------------------------------------------
    # Phase 12: Unsafe-Notify Validator
    # ----------------------------------------------------------------
    if _SAFETY_PIPELINE_AVAILABLE and safety_signals is not None and action == "notify":
        try:
            media_failed = bool(
                msg_ctx.media_analysis and
                getattr(msg_ctx.media_analysis, 'failure', False)
            )
            validator_result = prevent_unsafe_notify(
                proposed_action=action,
                safety_signals=safety_signals,
                deterministic_signals=msg_ctx.deterministic_signals,
                proposed_type=msg_type,
                proposed_reason=reason,
                proposed_evidence_ids=ev_ids,
                media_type=msg_ctx.media_type or '',
                media_failed=media_failed,
            )
            if validator_result.blocked:
                overrides.append(f"unsafe_notify_prevented_{validator_result.blocking_condition}")
                action = validator_result.final_action
                if validator_result.reason_adjustment:
                    reason = validator_result.reason_adjustment
                conf = max(0.0, conf + validator_result.confidence_adjustment)

        except Exception:
            pass  # graceful degradation

    # Final confidence clamp
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
