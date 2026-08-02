"""
Phase 14 Preclassifier — Deterministic preclassification and decision boundary tuning.
Determines if a message can be classified deterministically with high confidence
or requires model escalation.
"""
from typing import Dict, Any, Tuple, Optional
from schemas import (
    RouterInput,
    RouterProposal,
    ExecutionMode,
    RiskCategory
)

ALLOWED_MESSAGE_TYPES = {
    "personal", "urgent", "event", "payment", "business_update",
    "promotion", "greeting", "forward", "spam", "scam", "unknown"
}

ALLOWED_ACTIONS = {"notify", "digest", "mute"}

def preclassify_message(inp: RouterInput) -> Tuple[bool, RouterProposal, ExecutionMode, str]:
    """
    Evaluates grounded signals to preclassify action and message_type deterministically.
    Returns:
      (is_deterministic_direct, RouterProposal, ExecutionMode, escalation_reason)
    """
    text = inp.current_message_text.strip().lower() if inp.current_message_text else ""
    safety = inp.safety_signals
    interruption = inp.interruption_signals
    relevance = inp.relevance_signals
    temporal = inp.temporal_context
    
    # Default fallback proposal
    proposal = RouterProposal(
        action="digest",
        message_type="unknown",
        reason="Default heuristic preclassification",
        confidence=0.5,
        evidence_message_ids=["none"],
        provider="deterministic",
        model="preclassifier_v14"
    )
    
    # 1. Grounded Scam / Credential Risk -> High Certainty Mute/Scam
    if safety and (safety.credential_request or safety.risk_category == RiskCategory.CREDENTIAL_RISK):
        proposal.action = "mute"
        proposal.message_type = "scam"
        proposal.reason = "Unsolicited request for sensitive authentication credentials (OTP/password/PIN)"
        proposal.confidence = 0.98
        return True, proposal, ExecutionMode.DETERMINISTIC_DIRECT, "Grounded credential risk"
        
    if safety and safety.risk_category in (RiskCategory.PHISHING_RISK, RiskCategory.IMPERSONATION_RISK):
        proposal.action = "mute"
        proposal.message_type = "scam"
        proposal.reason = f"Security threat detected: {safety.risk_category.value} with coercive manipulation"
        proposal.confidence = 0.95
        return True, proposal, ExecutionMode.DETERMINISTIC_DIRECT, "Grounded phishing/impersonation risk"

    if safety and getattr(safety, "prompt_injection_signal", False):
        proposal.action = "mute"
        proposal.message_type = "scam"
        proposal.reason = "Prompt injection attempt detected trying to override router logic"
        proposal.confidence = 0.99
        return True, proposal, ExecutionMode.DETERMINISTIC_DIRECT, "Grounded prompt injection"


    # 2. Obvious Spam -> High Certainty Mute/Spam
    if safety and safety.risk_category == RiskCategory.SPAM:
        proposal.action = "mute"
        proposal.message_type = "spam"
        proposal.reason = "Unsolicited broadcast marketing content with no user relationship"
        proposal.confidence = 0.92
        return True, proposal, ExecutionMode.DETERMINISTIC_DIRECT, "Grounded spam"

    # 3. Simple Greetings -> High Certainty Digest/Greeting
    greetings = {"hi", "hello", "hey", "good morning", "good evening", "namaste", "gm", "gn"}
    clean_words = set(text.split())
    if len(clean_words) <= 3 and any(g in clean_words for g in greetings):
        proposal.action = "digest"
        proposal.message_type = "greeting"
        proposal.reason = "Simple conversational greeting with no actionable deadline or request"
        proposal.confidence = 0.90
        return True, proposal, ExecutionMode.DETERMINISTIC_DIRECT, "Simple greeting"

    # 4. Verified Payment Reminders -> Payment
    if safety and safety.payment_request:
        if safety.risk_category == RiskCategory.PAYMENT_RISK:
            proposal.action = "mute"
            proposal.message_type = "scam"
            proposal.reason = "Suspicious payment request with unverified details or coercive pressure"
            proposal.confidence = 0.93
            return True, proposal, ExecutionMode.DETERMINISTIC_DIRECT, "Suspicious payment risk"
        else:
            # Legitimate payment reminder
            proposal.message_type = "payment"
            if interruption and interruption.genuine_urgency:
                proposal.action = "notify"
                proposal.reason = "Legitimate payment due with immediate deadline"
                proposal.confidence = 0.91
            else:
                proposal.action = "digest"
                proposal.reason = "Legitimate payment reminder or statement"
                proposal.confidence = 0.88
            return True, proposal, ExecutionMode.DETERMINISTIC_DIRECT, "Legitimate payment"

    # 5. Clear Event / Meeting / Webinar -> Event
    event_keywords = {"webinar", "meeting", "scheduled for", "zoom link", "calendar invite", "appointment", "flight", "train"}
    if any(k in text for k in event_keywords):
        proposal.message_type = "event"
        if interruption and interruption.genuine_urgency and not (temporal and temporal.is_quiet_hours):
            proposal.action = "notify"
            proposal.reason = "Upcoming event starting imminently with concrete time reference"
            proposal.confidence = 0.90
        else:
            proposal.action = "digest"
            proposal.reason = "Scheduled event or appointment update"
            proposal.confidence = 0.87
        return True, proposal, ExecutionMode.DETERMINISTIC_DIRECT, "Clear event"

    # 6. Concrete Delivery / Waiting Outside -> Urgent
    if interruption and interruption.genuine_urgency:
        proposal.action = "notify"
        proposal.message_type = "urgent"
        proposal.reason = "Time-critical delivery or operational request requiring immediate attention"
        proposal.confidence = 0.92
        return True, proposal, ExecutionMode.DETERMINISTIC_DIRECT, "Concrete urgency"

    # 7. Business Updates & Promotions
    if "shipped" in text or "out for delivery" in text or "order update" in text or "tracking link" in text:
        proposal.message_type = "business_update"
        proposal.action = "digest"
        proposal.reason = "Standard operational business status update"
        proposal.confidence = 0.88
        return True, proposal, ExecutionMode.DETERMINISTIC_DIRECT, "Business update"

    if "discount" in text or "sale" in text or "off on all" in text or "limited offer" in text:
        proposal.message_type = "promotion"
        proposal.action = "digest" if not (safety and safety.risk_category == RiskCategory.PROMOTION_UNWANTED) else "mute"
        proposal.reason = "Promotional offer or marketing message"
        proposal.confidence = 0.89
        return True, proposal, ExecutionMode.DETERMINISTIC_DIRECT, "Promotion"

    # 8. Ambiguous / Personal Chat
    if relevance and relevance.personal_request:
        proposal.message_type = "personal"
        proposal.action = "notify" if (interruption and interruption.genuine_urgency) else "digest"
        proposal.reason = "Personal conversation message"
        proposal.confidence = 0.82
        return True, proposal, ExecutionMode.DETERMINISTIC_DIRECT, "Personal message"

    # Fallback to model escalation for highly complex ambiguous cases
    return False, proposal, ExecutionMode.NVIDIA_LIVE, "Ambiguous multi-signal message requiring model evaluation"
