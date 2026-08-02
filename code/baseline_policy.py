"""
Deterministic routing policy for Message Notification Router baseline_v1.
Evaluates extracted features and returns routing action, message type, confidence, and rule trace.
No hardcoded message IDs or sample labels.
"""

def route(features: dict, msg: dict) -> dict:
    """
    Route a message based on deterministic features.
    
    Returns:
        dict with keys: action, message_type, confidence, triggered_rules, confidence_components
    """
    action = None
    message_type = None
    confidence_base = 0.60
    triggered_rules = []
    rule_idx = 27

    # --- TIER 1: SAFETY GATE (produces mute + scam) ---
    if features.get("contains_prompt_injection"):
        action, message_type, confidence_base = "mute", "scam", 0.92
        triggered_rules.append("prompt_injection_detected")
        rule_idx = 1
    elif features.get("contains_otp_request") and (
        features.get("contains_account_block_threat")
        or features.get("contains_suspicious_link")
        or not features.get("sender_trusted_personal")
    ):
        action, message_type, confidence_base = "mute", "scam", 0.90
        triggered_rules.append("otp_scam")
        rule_idx = 2
    elif features.get("contains_credential_request") and not features.get("sender_trusted_personal"):
        action, message_type, confidence_base = "mute", "scam", 0.88
        triggered_rules.append("credential_request")
        rule_idx = 3
    elif features.get("contains_account_block_threat") and (
        features.get("contains_suspicious_link") or not features.get("business_is_verified")
    ):
        action, message_type, confidence_base = "mute", "scam", 0.87
        triggered_rules.append("account_block_scam")
        rule_idx = 4
    elif (
        features.get("contains_payment_pressure")
        and features.get("contains_qr_reference")
        and not features.get("business_is_verified")
    ):
        action, message_type, confidence_base = "mute", "scam", 0.86
        triggered_rules.append("qr_payment_scam")
        rule_idx = 5
    elif features.get("contains_lottery_claim") and not features.get("business_is_verified"):
        action, message_type, confidence_base = "mute", "scam", 0.85
        triggered_rules.append("lottery_scam")
        rule_idx = 6
    elif features.get("domain_mismatch") and features.get("business_reports_high"):
        action, message_type, confidence_base = "mute", "scam", 0.84
        triggered_rules.append("domain_mismatch_scam")
        rule_idx = 7
    elif features.get("contains_financial_data_request") and not features.get("sender_trusted_personal"):
        action, message_type, confidence_base = "mute", "scam", 0.88
        triggered_rules.append("financial_data_scam")
        rule_idx = 8

    # --- TIER 2: HIGH FORWARD SPAM ---
    elif features.get("high_forward_count") and features.get("historical_mute_signal"):
        action, message_type, confidence_base = "mute", "forward", 0.82
        triggered_rules.append("repeated_forward_muted")
        rule_idx = 9
    elif (
        features.get("high_forward_count")
        and features.get("historical_dismiss_signal")
        and not features.get("historical_reply_signal")
    ):
        action, message_type, confidence_base = "mute", "forward", 0.78
        triggered_rules.append("repeated_forward_dismissed")
        rule_idx = 10

    # --- TIER 3: EXPLICIT OPT-OUT ---
    elif features.get("user_opted_out") and features.get("contains_promotion_language"):
        action, message_type, confidence_base = "mute", "promotion", 0.82
        triggered_rules.append("opted_out_promotion")
        rule_idx = 11
    elif (
        features.get("historical_mute_signal")
        and not features.get("contains_immediate_time_reference")
        and not features.get("contains_deadline")
        and not features.get("sender_is_group_admin")
    ):
        msg_type = "promotion" if features.get("contains_promotion_language") else "spam"
        action, message_type, confidence_base = "mute", msg_type, 0.78
        triggered_rules.append("user_muted_similar")
        rule_idx = 12

    # --- TIER 4: NOTIFY CONDITIONS ---
    elif (
        not features.get("contains_prompt_injection")
        and features.get("contains_immediate_time_reference")
        and features.get("sender_is_group_admin")
        and not features.get("contains_suspicious_link")
        and not features.get("contains_otp_request")
    ):
        action, message_type, confidence_base = "notify", "urgent", 0.88
        triggered_rules.append("admin_operational_urgent")
        rule_idx = 13
    elif (
        features.get("contains_deadline")
        and (features.get("sender_is_group_admin") or features.get("sender_trusted_personal"))
        and not features.get("contains_suspicious_link")
    ):
        msg_type = "urgent" if features.get("contains_immediate_time_reference") else "event"
        action, message_type, confidence_base = "notify", msg_type, 0.86
        triggered_rules.append("trusted_sender_deadline")
        rule_idx = 14
    elif (
        features.get("business_is_verified")
        and features.get("user_has_active_transaction")
        and not features.get("domain_mismatch")
        and not features.get("contains_suspicious_link")
        and not features.get("contains_otp_request")
    ):
        action, message_type, confidence_base = "notify", "business_update", 0.88
        triggered_rules.append("verified_business_active_transaction")
        rule_idx = 15
    elif (
        features.get("contains_direct_mention")
        and (
            features.get("sender_is_group_admin")
            or features.get("sender_trusted_personal")
            or features.get("historical_reply_signal")
        )
        and features.get("contains_immediate_time_reference")
    ):
        action, message_type, confidence_base = "notify", "urgent", 0.85
        triggered_rules.append("direct_mention_urgent")
        rule_idx = 16
    elif (
        features.get("sender_trusted_personal")
        and features.get("contains_immediate_time_reference")
        and not features.get("contains_suspicious_link")
    ):
        action, message_type, confidence_base = "notify", "urgent", 0.84
        triggered_rules.append("trusted_personal_urgent")
        rule_idx = 17
    elif (
        features.get("contains_waiting_signal")
        and (
            features.get("sender_is_group_admin")
            or features.get("sender_trusted_personal")
            or features.get("business_is_verified")
        )
    ):
        msg_type = "urgent" if features.get("contains_immediate_time_reference") else "business_update"
        action, message_type, confidence_base = "notify", msg_type, 0.85
        triggered_rules.append("waiting_signal_trusted")
        rule_idx = 18

    # --- TIER 5: MUTE (high confidence history) ---
    elif features.get("historical_report_signal") and features.get("historical_dismiss_signal"):
        action, message_type, confidence_base = "mute", "spam", 0.80
        triggered_rules.append("report_and_dismiss_history")
        rule_idx = 19

    # --- TIER 6: DIGEST (useful non-urgent) ---
    elif (
        features.get("business_is_verified")
        and not features.get("user_opted_out")
        and not features.get("domain_mismatch")
        and features.get("contains_promotion_language")
    ):
        action, message_type, confidence_base = "digest", "promotion", 0.76
        triggered_rules.append("opted_in_business_promo")
        rule_idx = 20
    elif features.get("user_opted_in") and features.get("contains_promotion_language"):
        action, message_type, confidence_base = "digest", "promotion", 0.78
        triggered_rules.append("explicit_opt_in_promo")
        rule_idx = 21
    elif (
        features.get("contains_event_date")
        and not features.get("contains_immediate_time_reference")
        and not features.get("contains_suspicious_link")
    ):
        action, message_type, confidence_base = "digest", "event", 0.78
        triggered_rules.append("future_event")
        rule_idx = 22
    elif (
        features.get("business_is_verified")
        and not features.get("user_opted_out")
        and not features.get("domain_mismatch")
        and not features.get("contains_promotion_language")
    ):
        action, message_type, confidence_base = "digest", "business_update", 0.76
        triggered_rules.append("verified_business_non_urgent")
        rule_idx = 23
    elif features.get("contains_greeting") and not features.get("contains_suspicious_link"):
        action, message_type, confidence_base = "digest", "greeting", 0.76
        triggered_rules.append("harmless_greeting")
        rule_idx = 24
    elif (
        features.get("historical_dismiss_signal")
        and not features.get("contains_immediate_time_reference")
        and not features.get("sender_is_group_admin")
    ):
        action = "mute" if features.get("historical_mute_signal") else "digest"
        message_type = "promotion" if features.get("contains_promotion_language") else "personal"
        confidence_base = 0.74
        triggered_rules.append("dismiss_history_non_urgent")
        rule_idx = 25
    elif (
        features.get("sender_is_known")
        and not features.get("contains_suspicious_link")
        and not features.get("contains_otp_request")
    ):
        action, message_type, confidence_base = "digest", "personal", 0.74
        triggered_rules.append("known_sender_safe")
        rule_idx = 26

    # --- TIER 7: DEFAULT ---
    else:
        action, message_type, confidence_base = "digest", "unknown", 0.60
        triggered_rules.append("default_conservative")
        rule_idx = 27

    # --- CONFIDENCE ADJUSTMENTS ---
    components = {"base": confidence_base}
    adj = 0.0

    if features.get("historical_reply_signal"):
        adj += 0.04
        components["historical_reply_signal"] = 0.04
    if features.get("historical_dismiss_signal") and action in ("mute", "digest"):
        adj += 0.03
        components["historical_dismiss_signal"] = 0.03
    if features.get("historical_report_signal") and action == "mute":
        adj += 0.04
        components["historical_report_signal"] = 0.04
    if features.get("business_is_verified") and message_type in ("business_update", "promotion"):
        adj += 0.02
        components["business_is_verified"] = 0.02
    if features.get("user_has_active_transaction") and action == "notify":
        adj += 0.03
        components["user_has_active_transaction"] = 0.03
    if features.get("domain_mismatch") and message_type == "scam":
        adj += 0.03
        components["domain_mismatch"] = 0.03
    if features.get("context_missing"):
        adj -= 0.06
        components["context_missing"] = -0.06
    if features.get("media_present") and not features.get("media_available"):
        adj -= 0.04
        components["media_unavailable"] = -0.04
    if features.get("high_forward_count") and rule_idx >= 13:
        adj -= 0.02
        components["high_forward_noise"] = -0.02
    if rule_idx >= 24 or confidence_base < 0.70:
        adj -= 0.04
        components["low_specificity"] = -0.04

    final_conf = round(max(0.0, min(1.0, confidence_base + adj)), 2)

    return {
        "action": action,
        "message_type": message_type,
        "confidence": final_conf,
        "triggered_rules": triggered_rules,
        "confidence_components": components,
    }
