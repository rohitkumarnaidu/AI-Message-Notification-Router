"""
Phase 12 Safety Regression Tests — test_unsafe_notify_validator.py

Tests that scam/injection/credential signals always prevent 'notify' in routing.
Includes a graceful import test for unsafe_notify_validator.py (which may not exist yet).
All tests are deterministic — no API calls, no network.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))

from baseline_policy import route


# ============================================================
# CORE ROUTING SAFETY GUARANTEES
# ============================================================

def test_scam_type_must_not_notify():
    """OTP scam features must produce mute, never notify."""
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
    assert result['action'] != 'notify', (
        f"OTP scam must NEVER produce notify. Got action='{result['action']}' "
        f"rules={result['triggered_rules']}"
    )
    assert result['action'] == 'mute', (
        f"OTP scam must produce mute. Got action='{result['action']}'"
    )


def test_spam_type_must_not_notify():
    """User mute history + no deadline/time-ref must produce mute, not notify."""
    features = {
        'historical_mute_signal': True,
        'contains_immediate_time_reference': False,
        'contains_deadline': False,
        'sender_is_group_admin': False,
        'contains_otp_request': False,
        'contains_suspicious_link': False,
        'contains_prompt_injection': False,
        'contains_account_block_threat': False,
        'contains_credential_request': False,
    }
    result = route(features, {})
    assert result['action'] != 'notify', (
        f"Mute-history spam must not produce notify, got '{result['action']}' "
        f"rules={result['triggered_rules']}"
    )
    assert result['action'] == 'mute', (
        f"Mute-history spam must produce mute, got '{result['action']}'"
    )


def test_prompt_injection_must_not_notify():
    """Detected prompt injection must always route to mute/scam, never notify."""
    features = {
        'contains_prompt_injection': True,
        'sender_is_group_admin': True,       # even admin cannot override injection block
        'contains_immediate_time_reference': True,
        'contains_suspicious_link': False,
        'contains_otp_request': False,
        'contains_account_block_threat': False,
        'contains_credential_request': False,
    }
    result = route(features, {})
    assert result['action'] == 'mute', (
        f"Prompt injection must always produce mute. Got '{result['action']}' "
        f"rules={result['triggered_rules']}"
    )
    assert result['message_type'] == 'scam', (
        f"Prompt injection must produce message_type='scam'. Got '{result['message_type']}'"
    )


def test_no_relevance_greeting_should_digest():
    """A plain greeting with no urgency and no dismiss history should digest, not notify."""
    features = {
        'contains_greeting': True,
        'historical_dismiss_signal': False,
        'contains_immediate_time_reference': False,
        'contains_otp_request': False,
        'contains_suspicious_link': False,
        'contains_prompt_injection': False,
        'contains_account_block_threat': False,
        'contains_credential_request': False,
        'sender_is_group_admin': False,
        'sender_trusted_personal': False,
        'business_is_verified': False,
    }
    result = route(features, {})
    assert result['action'] == 'digest', (
        f"Greeting with no urgency should digest. Got action='{result['action']}' "
        f"rules={result['triggered_rules']}"
    )
    assert result['action'] != 'notify', (
        f"Plain greeting must not produce notify, got '{result['action']}'"
    )


def test_credential_risk_cannot_notify():
    """OTP request + account block threat + untrusted sender must produce mute/scam."""
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
        f"Credential risk must produce mute. Got '{result['action']}'"
    )
    assert result['message_type'] == 'scam', (
        f"Credential risk must produce message_type='scam'. Got '{result['message_type']}'"
    )


def test_genuine_urgent_preserved():
    """Genuine urgent message from group admin with no risk signals must produce notify."""
    features = {
        'sender_is_group_admin': True,
        'contains_immediate_time_reference': True,
        'contains_suspicious_link': False,
        'contains_otp_request': False,
        'contains_account_block_threat': False,
        'contains_credential_request': False,
        'contains_prompt_injection': False,
        'business_is_verified': False,
    }
    result = route(features, {})
    assert result['action'] == 'notify', (
        f"Genuine group admin urgent must produce notify. Got '{result['action']}' "
        f"rules={result['triggered_rules']}"
    )


# ============================================================
# UNSAFE NOTIFY VALIDATOR — GRACEFUL IMPORT TEST
# ============================================================

def test_unsafe_notify_validator_import():
    """
    Try to import unsafe_notify_validator from code/.
    If the module exists, verify it exposes prevent_unsafe_notify.
    If it does not exist yet, skip the test gracefully.
    """
    try:
        import unsafe_notify_validator as unv
    except ModuleNotFoundError:
        pytest.skip(
            "unsafe_notify_validator.py not yet present — skipping import test. "
            "This test will auto-activate once the module is created."
        )

    assert hasattr(unv, 'prevent_unsafe_notify'), (
        "unsafe_notify_validator must expose a 'prevent_unsafe_notify' function. "
        f"Found attributes: {[a for a in dir(unv) if not a.startswith('_')]}"
    )
    assert callable(getattr(unv, 'prevent_unsafe_notify')), (
        "unsafe_notify_validator.prevent_unsafe_notify must be callable."
    )
