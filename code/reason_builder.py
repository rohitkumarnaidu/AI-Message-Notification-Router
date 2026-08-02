"""
Reason builder for Message Notification Router baseline_v1.
Constructs transparent, non-generic explanations based on triggered rules and features.
Max 200 characters. Never claims unseen media content or fabricated user preferences.
"""

_RULE_REASONS = {
    "prompt_injection_detected": "The message attempts to override routing instructions, which is a strong scam indicator.",
    "otp_scam": "The message requests an OTP through an unfamiliar or suspicious flow, which is a strong scam indicator.",
    "credential_request": "The message asks for sensitive credentials (password, PIN, or login code) and cannot be verified as safe.",
    "account_block_scam": "The message uses fake account-blocking pressure",
    "qr_payment_scam": "The message combines QR-code payment pressure with an unverified sender, which is a known scam pattern.",
    "lottery_scam": "The message claims the user has won a prize or reward, which is a classic scam pattern.",
    "domain_mismatch_scam": "The sender domain does not match the business official domain and the account has a high report count.",
    "financial_data_scam": "The message requests financial account details from an unverified source.",
    "repeated_forward_muted": "The message is highly forwarded and the user has previously muted similar content from this sender.",
    "repeated_forward_dismissed": "The message is highly forwarded and the user has a pattern of dismissing similar forwards.",
    "opted_out_promotion": "The user has opted out of similar promotions from this sender or category.",
    "user_muted_similar": "The user has previously muted messages similar to this one.",
    "admin_operational_urgent": "A group admin sent a time-sensitive operational update that requires immediate attention.",
    "trusted_sender_deadline": "A trusted sender sent a message with a concrete deadline or time-sensitive action required.",
    "verified_business_active_transaction": "A verified business sent an update matching the user's recent order or booking history.",
    "direct_mention_urgent": "The user is directly mentioned in a time-sensitive context requiring a response.",
    "trusted_personal_urgent": "A trusted contact sent an immediate request requiring a quick response.",
    "waiting_signal_trusted": "A trusted sender indicates something is waiting or about to leave, requiring immediate action.",
    "report_and_dismiss_history": "The user has previously reported and dismissed similar messages from this source.",
    "opted_in_business_promo": "The promotion is from a verified business and the user has not opted out.",
    "explicit_opt_in_promo": "The user explicitly opted into messages from this business.",
    "future_event": "The message contains a future event or deadline that can be reviewed later.",
    "verified_business_non_urgent": "The verified business message is legitimate but does not require immediate attention.",
    "harmless_greeting": "The message is a harmless greeting that can be read at the user's convenience.",
    "dismiss_history_non_urgent": "The user has a history of dismissing similar messages and this one has no urgent action required.",
    "known_sender_safe": "The sender is known and the message does not contain safety risks or urgent action.",
    "default_conservative": "The message does not match any high-priority pattern and is routed conservatively for later review.",
}


def build_reason(
    action: str,
    message_type: str,
    triggered_rules: list[str],
    features: dict,
    msg: dict,
) -> str:
    """
    Build a human-readable reason string (max 200 chars) explaining the decision.
    """
    rule = triggered_rules[0] if triggered_rules else "default_conservative"
    reason = _RULE_REASONS.get(rule, _RULE_REASONS["default_conservative"])

    # Dynamic additions for specific rules
    if rule == "otp_scam" and features.get("contains_suspicious_link"):
        reason += " A suspicious link was also detected."
    elif rule == "account_block_scam":
        if features.get("contains_suspicious_link"):
            reason += " combined with a suspicious link."
        else:
            reason += " to push the user into action."

    # Context additions
    if features.get("media_present") and not features.get("media_available"):
        reason += " Media content was unavailable for analysis, reducing confidence."
    if features.get("context_missing"):
        reason += " Some context was missing, which reduces routing confidence."

    # Trim to 200 chars cleanly if needed
    reason = " ".join(reason.split())
    if len(reason) > 200:
        reason = reason[:197].rstrip() + "..."

    return reason
