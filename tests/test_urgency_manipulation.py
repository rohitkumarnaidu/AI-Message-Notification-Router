"""
Phase 12 Safety Regression Tests — test_urgency_manipulation.py

Tests distinguishing genuine urgency from manipulative pressure,
and verifying the routing policy handles them correctly.
All tests are deterministic — no API calls, no network.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))

from safety_detectors import detect_urgency
from baseline_policy import route


# ============================================================
# DETECTOR — GENUINE URGENCY
# ============================================================

def test_genuine_delivery_waiting():
    """'Delivery person is waiting outside' must have has_concrete=True."""
    has_urgency, has_concrete, is_future, sources = detect_urgency(
        'Delivery person is waiting outside your building'
    )
    assert has_concrete is True, (
        f"Expected has_concrete=True for 'waiting outside', got {has_concrete}"
    )


def test_genuine_flight_arriving():
    """'Your flight departs in 30 minutes' must have has_concrete=True."""
    has_urgency, has_concrete, is_future, sources = detect_urgency(
        'Your flight departs in 30 minutes, please hurry'
    )
    assert has_concrete is True, (
        f"Expected has_concrete=True for flight departure in 30 min, got {has_concrete}"
    )


# ============================================================
# DETECTOR — VAGUE / FAKE URGENCY
# ============================================================

def test_fake_urgency_no_deadline():
    """'URGENT please respond immediately' has vague urgency but no concrete deadline."""
    has_urgency, has_concrete, is_future, sources = detect_urgency(
        'This is URGENT please respond immediately'
    )
    assert has_urgency is True, (
        f"Expected has_urgency=True for URGENT keyword, got {has_urgency}"
    )
    assert has_concrete is False, (
        f"Expected has_concrete=False (no specific deadline), got {has_concrete}"
    )


def test_future_event_not_urgent():
    """Webinar scheduled for next week is a future event, not immediate urgency."""
    has_urgency, has_concrete, is_future, sources = detect_urgency(
        'Join us for the webinar next week on Thursday'
    )
    assert is_future is True, (
        f"Expected is_future=True for 'next week', got {is_future}"
    )
    assert has_concrete is False, (
        f"Expected has_concrete=False for future-dated event, got {has_concrete}"
    )


def test_stale_deadline_pattern():
    """'Offer was valid until yesterday' is past — must not be a concrete future deadline."""
    has_urgency, has_concrete, is_future, sources = detect_urgency(
        'Offer was valid until yesterday'
    )
    # 'yesterday' is not in future event patterns and not in concrete deadline patterns
    assert is_future is False, (
        f"Expected is_future=False for past offer, got {is_future}"
    )
    assert has_concrete is False, (
        f"Expected has_concrete=False for stale deadline, got {has_concrete}"
    )


# ============================================================
# ROUTING POLICY — SCAM URGENCY vs GENUINE URGENCY
# ============================================================

def test_account_block_as_scam_not_urgency():
    """Account block threat with suspicious link and no verified business → mute/scam."""
    features = {
        'contains_account_block_threat': True,
        'business_is_verified': False,
        'contains_suspicious_link': True,
        'contains_prompt_injection': False,
        'contains_otp_request': False,
        'contains_credential_request': False,
        'sender_trusted_personal': False,
    }
    result = route(features, {})
    assert result['action'] == 'mute', (
        f"Expected mute for account block scam, got '{result['action']}'"
    )
    assert result['message_type'] == 'scam', (
        f"Expected message_type='scam', got '{result['message_type']}'"
    )


def test_admin_urgent_operational():
    """Group admin + immediate time reference + no suspicious signals → notify/urgent."""
    features = {
        'sender_is_group_admin': True,
        'contains_immediate_time_reference': True,
        'contains_suspicious_link': False,
        'contains_otp_request': False,
        'contains_account_block_threat': False,
        'contains_credential_request': False,
        'contains_prompt_injection': False,
        'business_is_verified': False,
        'sender_trusted_personal': False,
    }
    result = route(features, {})
    assert result['action'] == 'notify', (
        f"Expected notify for admin operational urgent, got '{result['action']}' "
        f"rules={result['triggered_rules']}"
    )
    assert result['message_type'] in ('urgent', 'event'), (
        f"Expected message_type in ('urgent', 'event'), got '{result['message_type']}'"
    )


def test_quiet_hours_non_urgent():
    """During quiet hours, a non-urgent message without time references must be digested."""
    # The router doesn't have a quiet_hours_active feature key; instead absence of
    # immediate_time_reference combined with no scam signals defaults to digest.
    features = {
        'contains_immediate_time_reference': False,
        'sender_is_group_admin': False,
        'contains_otp_request': False,
        'contains_account_block_threat': False,
        'contains_suspicious_link': False,
        'contains_credential_request': False,
        'contains_prompt_injection': False,
        'business_is_verified': False,
        'sender_trusted_personal': False,
        'contains_greeting': True,  # a greeting — harmless, should be digest
    }
    result = route(features, {})
    # A greeting with no urgency signals should digest, not notify
    assert result['action'] in ('digest', 'mute'), (
        f"Expected digest (or mute) for non-urgent quiet-hour message, got '{result['action']}'"
    )
    assert result['action'] != 'notify', (
        f"Non-urgent message must NOT be notified during quiet-equivalent conditions, "
        f"got action='{result['action']}'"
    )
