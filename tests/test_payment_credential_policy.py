"""
Phase 12 Safety Regression Tests — test_payment_credential_policy.py

Tests payment and credential detection combined with baseline routing policy.
All tests are deterministic — no API calls, no network.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))

from safety_detectors import detect_credential_risk, detect_payment_risk
from baseline_policy import route


# ============================================================
# ROUTING POLICY — PAYMENT TESTS
# ============================================================

def test_legitimate_payment_not_muted():
    """Verified business payment reminder without pressure must NOT be muted."""
    features = {
        'business_is_verified': True,
        'contains_immediate_time_reference': False,
        'contains_payment_pressure': False,
        'historical_reply_signal': True,
        'contains_otp_request': False,
        'contains_suspicious_link': False,
        'contains_prompt_injection': False,
        'contains_account_block_threat': False,
        'contains_credential_request': False,
        'contains_qr_reference': False,
        'user_has_active_transaction': True,
        'domain_mismatch': False,
    }
    result = route(features, {})
    assert result['action'] != 'mute', (
        f"Legitimate payment reminder must NOT be muted, got action='{result['action']}' "
        f"rules={result['triggered_rules']}"
    )
    assert result['action'] in ('notify', 'digest'), (
        f"Expected notify or digest for verified payment, got '{result['action']}'"
    )


def test_suspicious_qr_no_business():
    """QR + payment pressure with no verified business must trigger mute/qr_payment_scam."""
    features = {
        'contains_qr_reference': True,
        'contains_payment_pressure': True,
        'business_is_verified': False,
        'contains_prompt_injection': False,
        'contains_otp_request': False,
        'contains_account_block_threat': False,
        'contains_suspicious_link': False,
        'contains_credential_request': False,
    }
    result = route(features, {})
    assert result['action'] == 'mute', (
        f"Expected mute for QR scam, got action='{result['action']}'"
    )
    assert 'qr_payment_scam' in result['triggered_rules'], (
        f"Expected 'qr_payment_scam' rule, got rules={result['triggered_rules']}"
    )


def test_official_app_no_credential():
    """Verified business shipment tracking message with no risk signals must NOT be muted."""
    features = {
        'business_is_verified': True,
        'contains_otp_request': False,
        'contains_credential_request': False,
        'contains_suspicious_link': False,
        'contains_account_block_threat': False,
        'contains_prompt_injection': False,
        'contains_qr_reference': False,
        'contains_payment_pressure': False,
        'domain_mismatch': False,
        'user_has_active_transaction': True,
    }
    result = route(features, {})
    assert result['action'] != 'mute', (
        f"Verified business shipment tracking must NOT be muted, got '{result['action']}' "
        f"rules={result['triggered_rules']}"
    )


# ============================================================
# DETECTOR — CREDENTIAL TESTS
# ============================================================

def test_otp_request_trusted_sender():
    """Trust does NOT override credential risk — request must still be flagged."""
    # Matches _CRED_REQUEST_PATTERNS[3]: (enter|type|provide|submit).{0,20}(password|pin|otp|code)
    is_request, is_warning, sources = detect_credential_risk(
        'enter your OTP to verify', trusted_source=True
    )
    assert is_request is True, (
        "Trusted source must NOT suppress OTP credential request detection; "
        f"expected is_request=True, got {is_request}"
    )


def test_otp_request_verified_business():
    """Credential request without trusted source must be detected regardless."""
    # Matches _CRED_REQUEST_PATTERNS[1]: (share|send|give|tell|reply) ... (otp|code|pin|password)
    is_request, is_warning, sources = detect_credential_risk(
        'share your verification code with me', trusted_source=False
    )
    assert is_request is True, (
        f"Expected is_request=True for 'share your verification code', got {is_request}"
    )


# ============================================================
# DETECTOR — PAYMENT TESTS
# ============================================================

def test_payment_with_existing_order_and_verified_business():
    """EMI payment due reminder must trigger has_legit=True and is_suspicious=False."""
    # Matches _LEGITIMATE_PAYMENT_INDICATORS[3]: (emi|installment|premium)\s*(due|payment)
    text = 'Your EMI payment is due for this month'
    payment_request, is_suspicious, has_legit, qr_present, sources = detect_payment_risk(
        text, business_relationship=True, trusted_sender=False
    )
    assert has_legit is True, (
        f"Expected has_legit=True for EMI payment reminder, got {has_legit}"
    )
    assert is_suspicious is False, (
        f"Expected is_suspicious=False for legitimate EMI, got {is_suspicious}"
    )


def test_payment_with_suspicious_link():
    """Urgent payment link to unrecognized domain must be flagged as suspicious."""
    text = 'Pay now at pay-check.net/urgent'
    payment_request, is_suspicious, has_legit, qr_present, sources = detect_payment_risk(
        text, business_relationship=False
    )
    assert is_suspicious is True, (
        f"Expected is_suspicious=True for urgent link at shady domain, got {is_suspicious}"
    )


def test_refund_bait():
    """Refund claim + pay processing fee is a classic refund bait scam."""
    # Matches _PAYMENT_REQUEST_PATTERNS[3]:
    # (refund|cashback|prize)\s*(claim|get|collect).{0,30}(pay|fee|charge|deposit)
    text = 'Claim your refund now Pay Rs 100 processing fee'
    payment_request, is_suspicious, has_legit, qr_present, sources = detect_payment_risk(text)
    assert is_suspicious is True, (
        f"Expected is_suspicious=True for refund bait scam, got {is_suspicious}"
    )


# ============================================================
# ROUTING POLICY — CREDENTIAL TESTS
# ============================================================

def test_credential_risk_routes_to_mute():
    """OTP request from untrusted sender + account block threat must route to mute/scam."""
    features = {
        'contains_otp_request': True,
        'sender_trusted_personal': False,
        'contains_account_block_threat': True,
        'contains_suspicious_link': False,
        'contains_prompt_injection': False,
        'contains_credential_request': True,
        'business_is_verified': False,
    }
    result = route(features, {})
    assert result['action'] == 'mute', (
        f"Expected mute for OTP scam with account block threat, got '{result['action']}'"
    )
    assert result['message_type'] == 'scam', (
        f"Expected message_type='scam', got '{result['message_type']}'"
    )
