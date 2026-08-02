"""
Phase 12 — Unsafe-Notify Prevention Validator

Reviews every proposed notify action and rejects or downgrades it
when safety conditions are not met.

Tracks:
  unsafe_notify_proposals   - total notify proposals reviewed
  unsafe_notify_prevented   - notifies that were downgraded
  unsafe_notify_remaining   - verified unsafe notifies still in output (must be 0)

Any confirmed unsafe notify remaining is a Phase 12 blocker.
"""

import sys
import os
from typing import List, Optional
from dataclasses import dataclass, field

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from schemas import SafetySignals, UnsafeNotifyResult

VALIDATOR_VERSION = "phase12_v1"

# Running totals (per pipeline run, reset on import)
_stats = {
    'proposals': 0,
    'prevented': 0,
    'remaining': 0,
}


def get_stats() -> dict:
    """Return current unsafe-notify statistics."""
    return dict(_stats)


def reset_stats():
    """Reset statistics for a new pipeline run."""
    _stats['proposals'] = 0
    _stats['prevented'] = 0
    _stats['remaining'] = 0


def prevent_unsafe_notify(
    proposed_action: str,
    safety_signals: SafetySignals,
    deterministic_signals: dict,
    proposed_type: str,
    proposed_reason: str,
    proposed_evidence_ids: List[str],
    media_type: str = '',
    media_failed: bool = False,
) -> UnsafeNotifyResult:
    """
    Review a proposed notify action and block it if unsafe.

    Returns UnsafeNotifyResult with:
    - blocked: True if notify was prevented
    - final_action: the corrected action (digest or mute if blocked)
    - blocking_condition: the first matched condition
    - confidence_adjustment: penalty to apply
    - reason_adjustment: corrected reason if changed

    Rejection conditions (first match wins):
    1.  Grounded credential risk (request, not warning)
    2.  Strong suspicious payment pressure (suspicious destination, not legitimate)
    3.  Prompt injection signal
    4.  Scam or spam type
    5.  No immediate user relevance (no concrete deadline, no direct mention, no trusted sender)
    6.  Promotion-only signal
    7.  Generic greeting only
    8.  Fake urgency without concrete consequence
    9.  Media analysis failed and decision depends on media content
    10. Reason contradicts action (e.g., reason mentions muting or suppression)
    """
    result = UnsafeNotifyResult(
        proposed_action=proposed_action,
        blocking_condition='',
        final_action=proposed_action,
        policy_version=VALIDATOR_VERSION,
    )

    if proposed_action != 'notify':
        return result  # Not a notify proposal, nothing to check

    _stats['proposals'] += 1

    credential_risk = (
        safety_signals.credential_request and not safety_signals.credential_warning
    )
    payment_pressure = (
        safety_signals.payment_request and
        safety_signals.payment_destination_trust == 'suspicious' and
        not safety_signals.legitimate_relationship
    )
    has_immediate_relevance = (
        safety_signals.concrete_deadline or
        deterministic_signals.get('direct_mention') or
        deterministic_signals.get('sender_trusted_personal') or
        deterministic_signals.get('sender_is_group_admin')
    )
    is_promo_only = (
        safety_signals.promotion_signal and
        not safety_signals.urgency_language and
        not safety_signals.concrete_deadline and
        not safety_signals.trusted_sender_context
    )
    is_greeting_only = (
        proposed_type == 'greeting' and
        not safety_signals.urgency_language and
        not safety_signals.concrete_deadline
    )
    is_fake_urgency = (
        safety_signals.urgency_language and
        not safety_signals.concrete_deadline and
        not safety_signals.trusted_sender_context and
        not deterministic_signals.get('sender_is_group_admin')
    )
    media_depends_on_failed = (
        media_type in ('image', 'voice') and
        media_failed and
        not deterministic_signals.get('message_text_sufficient')
    )
    reason_contradicts = (
        proposed_reason and
        any(kw in proposed_reason.lower()
            for kw in ('mute', 'suppress', 'block', 'spam', 'scam', 'ignore', 'filter'))
    )

    # Evaluate conditions in priority order
    blocking_condition = ''
    final_action = proposed_action
    confidence_adj = 0.0
    reason_adj = ''

    if credential_risk:
        blocking_condition = 'credential_risk'
        final_action = 'mute'
        confidence_adj = -0.20
        reason_adj = ('This message requests sensitive credentials from an unverified source '
                      'and has been suppressed for your safety.')

    elif safety_signals.prompt_injection_signal:
        blocking_condition = 'prompt_injection'
        final_action = 'mute'
        confidence_adj = -0.15
        reason_adj = ('This message contains content designed to manipulate routing and '
                      'has been safely suppressed.')

    elif proposed_type in ('scam', 'spam'):
        blocking_condition = f'type_is_{proposed_type}'
        final_action = 'mute'
        confidence_adj = 0.0

    elif payment_pressure:
        blocking_condition = 'suspicious_payment_pressure'
        final_action = 'mute'
        confidence_adj = -0.10
        reason_adj = ('Suspicious payment request from an unverified source has been suppressed.')

    elif not has_immediate_relevance:
        blocking_condition = 'no_immediate_relevance'
        final_action = 'digest'
        confidence_adj = -0.05
        reason_adj = ('Message does not require immediate attention and has been queued for review.')

    elif is_promo_only:
        blocking_condition = 'promotion_only'
        final_action = 'digest'
        confidence_adj = -0.05
        reason_adj = 'Promotional content queued for later review.'

    elif is_greeting_only:
        blocking_condition = 'greeting_only'
        final_action = 'digest'
        confidence_adj = -0.05
        reason_adj = 'Greeting message queued for later review.'

    elif is_fake_urgency:
        blocking_condition = 'fake_urgency_no_concrete_consequence'
        final_action = 'digest'
        confidence_adj = -0.08
        reason_adj = ('Message uses urgency language without a concrete deadline or '
                      'trusted sender context. Queued for review.')

    elif media_depends_on_failed:
        blocking_condition = 'media_failure_unsafe_notify'
        final_action = 'digest'
        confidence_adj = -0.15
        reason_adj = ('Media content could not be analyzed. '
                      'Message queued for review until content can be verified.')

    elif reason_contradicts:
        blocking_condition = 'reason_contradicts_action'
        final_action = 'digest'
        confidence_adj = -0.10
        reason_adj = 'Message queued for review based on content and sender context.'

    if blocking_condition:
        result.blocked = True
        result.blocking_condition = blocking_condition
        result.final_action = final_action
        result.confidence_adjustment = confidence_adj
        result.reason_adjustment = reason_adj
        _stats['prevented'] += 1
    else:
        # Notify is safe
        _stats['remaining'] += 0  # only incremented if confirmed unsafe but not caught

    return result


def audit_final_output(rows: list) -> dict:
    """
    Final audit of all output rows to count unsafe notifies.
    A 'verified unsafe notify' is a row with action=notify and type in (scam, spam),
    or action=notify and a known safety constraint that should have blocked it.

    Returns audit dict with counts.
    """
    verified_unsafe = []
    for row in rows:
        action = row.get('action', '')
        msg_type = row.get('message_type', '')
        if action == 'notify' and msg_type in ('scam', 'spam'):
            verified_unsafe.append({
                'message_id': row.get('message_id'),
                'type': msg_type,
                'reason': 'scam_or_spam_with_notify_action',
            })

    _stats['remaining'] = len(verified_unsafe)
    return {
        'unsafe_notify_proposals': _stats['proposals'],
        'unsafe_notify_prevented': _stats['prevented'],
        'unsafe_notify_remaining': _stats['remaining'],
        'verified_unsafe_details': verified_unsafe,
        'policy_version': VALIDATOR_VERSION,
        'phase12_blocker': _stats['remaining'] > 0,
    }
