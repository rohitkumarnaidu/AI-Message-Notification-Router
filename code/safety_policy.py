"""
Phase 12 — Deterministic Safety Policy Resolver

Resolves the final routing decision by combining:
- Router/model proposal (lowest trust for safety-critical paths)
- SafetySignals from deterministic detectors
- Urgency signals
- User personalization context
- Media and evidence quality

Priority order (descending):
1. Output/schema integrity
2. Grounded credential + high-risk scam constraints
3. Prompt/tool-instruction isolation
4. Dangerous content constraints
5. Legitimate immediate safety/access need
6. User-specific relevance
7. Quiet hours / load / mute state
8. Promotion and low-value policy
9. Model proposal
10. Conservative fallback

CRITICAL: Model output does NOT precede deterministic high-risk constraints.
"""

import sys
import os
from typing import List, Optional, Any

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from schemas import (
    SafetySignals, PolicyDecision, ExecutionTrace, RiskCategory,
    IncomingMessageContext
)

POLICY_VERSION = "phase12_v1"


def _grounded_reason(signals: SafetySignals, risk_category: str,
                      action: str, msg_type: str) -> str:
    """
    Build a grounded, natural-language reason from detected signals.
    - Cites concrete signals, not internal rule IDs or provider names.
    - Does NOT expose sensitive content unnecessarily.
    - Does NOT tell the user to share credentials.
    """
    sources = (
        signals.credential_sources +
        signals.payment_sources +
        signals.pressure_sources +
        signals.injection_sources +
        signals.urgency_sources
    )
    # Pick the highest-confidence grounded fragment
    top_source = max(sources, key=lambda s: s.confidence, default=None)

    if risk_category == RiskCategory.CREDENTIAL_RISK.value:
        return ("This message appears to request sensitive account credentials "
                "from an unverified source. Such requests are not made by legitimate services "
                "through messaging apps.")

    if risk_category == RiskCategory.PHISHING_RISK.value:
        if signals.reward_or_lottery:
            return ("This message claims a prize or reward with no verifiable basis. "
                    "Unsolicited reward claims are a common phishing pattern.")
        if signals.account_blocking_pressure:
            return ("This message threatens account restriction to create urgency. "
                    "Legitimate services do not send account-blocking threats via WhatsApp.")
        return ("This message shows multiple signals consistent with a phishing attempt, "
                "including unverified sender claims and pressure tactics.")

    if risk_category == RiskCategory.PAYMENT_RISK.value:
        if signals.qr_present and signals.payment_destination_trust == 'suspicious':
            return ("This message requests an immediate payment via QR code from an unverified source. "
                    "Verify the request through official channels before proceeding.")
        return ("This message contains payment pressure from an unverified or mismatched source. "
                "The payment context does not match a known transaction.")

    if risk_category == RiskCategory.PROMPT_INJECTION.value:
        return ("This message contains content that appears designed to manipulate routing behavior. "
                "It has been safely suppressed.")

    if risk_category == RiskCategory.IMPERSONATION_RISK.value:
        return ("This message claims authority from a government or official body, "
                "which cannot be verified through this channel.")

    if risk_category == RiskCategory.DANGEROUS_FORWARD.value:
        return ("This message has been forwarded many times and matches a pattern of "
                "previously muted content from this sender.")

    if risk_category == RiskCategory.PROMOTION_UNWANTED.value:
        return ("Promotional content from a sender you have previously opted out of.")

    if risk_category == RiskCategory.SPAM.value:
        return ("This message matches a pattern of unsolicited bulk content you have previously muted.")

    if action == 'notify':
        if signals.concrete_deadline:
            return ("Time-sensitive message with a concrete immediate deadline requiring your attention.")
        if signals.trusted_sender_context:
            return ("Direct message from a trusted contact requiring your attention.")
        return ("Message requires your immediate attention based on content and sender context.")

    if action == 'digest':
        if signals.promotion_signal:
            return ("Promotional update queued for your review at a convenient time.")
        if signals.business_relationship:
            return ("Business update from a service you use, queued for later review.")
        return ("Non-urgent message from a known sender, queued for your next review.")

    # Generic fallback
    return ("Message routed based on content patterns and sender context. "
            "No immediate action is required.")


def resolve_policy(
    proposed_action: str,
    proposed_type: str,
    proposed_reason: str,
    proposed_confidence: float,
    proposed_evidence_ids: List[str],
    safety_signals: SafetySignals,
    deterministic_signals: dict,
    media_quality: str = 'none',
    evidence_quality: str = 'none',
) -> PolicyDecision:
    """
    Apply deterministic safety policy over the router/model proposal.

    Returns PolicyDecision with final action, type, overrides, confidence bounds, and trace.
    """
    trace: List[str] = []
    overrides: List[ExecutionTrace] = []
    action = proposed_action
    msg_type = proposed_type
    reason = proposed_reason
    confidence_ceiling = 0.99
    confidence_floor = 0.0
    override_applied = False
    override_code = ''

    step = 0

    # ----------------------------------------------------------------
    # PRIORITY 1 — SCHEMA INTEGRITY
    # ----------------------------------------------------------------
    step += 1
    from schemas import ALLOWED_ACTIONS, ALLOWED_MESSAGE_TYPES
    if action not in ALLOWED_ACTIONS:
        overrides.append(ExecutionTrace(step, 'schema_action_fix', action, msg_type, 'digest', msg_type,
                                         f'Invalid action {action!r} corrected to digest'))
        action = 'digest'
        override_applied = True
        override_code = 'schema_action_fix'
        trace.append(f'step{step}: schema_action_fix')

    if msg_type not in ALLOWED_MESSAGE_TYPES:
        overrides.append(ExecutionTrace(step, 'schema_type_fix', action, msg_type, action, 'unknown',
                                         f'Invalid type {msg_type!r} corrected to unknown'))
        msg_type = 'unknown'
        override_applied = True
        trace.append(f'step{step}: schema_type_fix')

    # ----------------------------------------------------------------
    # PRIORITY 2 — GROUNDED CREDENTIAL + HIGH-RISK SCAM CONSTRAINTS
    # ----------------------------------------------------------------
    step += 1
    risk_cat = safety_signals.risk_category
    risk_tier = safety_signals.risk_tier

    credential_risk_active = (
        safety_signals.credential_request and
        not safety_signals.credential_warning  # warning is safe, request is not
    )

    if credential_risk_active:
        if action != 'mute' or msg_type != 'scam':
            overrides.append(ExecutionTrace(step, 'credential_risk_constraint', action, msg_type,
                                             'mute', 'scam',
                                             'Grounded credential request from unverified source.'))
            action = 'mute'
            msg_type = 'scam'
            override_applied = True
            override_code = 'credential_risk_constraint'
            confidence_ceiling = 0.95
            confidence_floor = 0.70
            trace.append(f'step{step}: credential_risk_constraint')
        reason = _grounded_reason(safety_signals, RiskCategory.CREDENTIAL_RISK.value, action, msg_type)

    elif safety_signals.reward_or_lottery and not safety_signals.legitimate_relationship:
        if action == 'notify':
            overrides.append(ExecutionTrace(step, 'phishing_reward_constraint', action, msg_type,
                                             'mute', 'scam', 'Unverified reward claim detected.'))
            action = 'mute'
            msg_type = 'scam'
            override_applied = True
            override_code = 'phishing_reward_constraint'
            confidence_ceiling = 0.92
            trace.append(f'step{step}: phishing_reward_constraint')
            reason = _grounded_reason(safety_signals, RiskCategory.PHISHING_RISK.value, action, msg_type)

    elif (safety_signals.account_blocking_pressure and
          (safety_signals.suspicious_link or not safety_signals.business_relationship)):
        if action == 'notify':
            overrides.append(ExecutionTrace(step, 'account_block_scam_constraint', action, msg_type,
                                             'mute', 'scam', 'Account blocking threat with no verified relationship.'))
            action = 'mute'
            msg_type = 'scam'
            override_applied = True
            override_code = 'account_block_scam_constraint'
            confidence_ceiling = 0.90
            trace.append(f'step{step}: account_block_scam_constraint')
            reason = _grounded_reason(safety_signals, RiskCategory.PHISHING_RISK.value, action, msg_type)

    # ----------------------------------------------------------------
    # PRIORITY 3 — PROMPT INJECTION ISOLATION
    # ----------------------------------------------------------------
    step += 1
    if safety_signals.prompt_injection_signal:
        if action != 'mute':
            overrides.append(ExecutionTrace(step, 'prompt_injection_isolation', action, msg_type,
                                             'mute', 'scam',
                                             'Content attempting to manipulate routing detected.'))
            action = 'mute'
            msg_type = 'scam'
            override_applied = True
            override_code = 'prompt_injection_isolation'
            confidence_ceiling = 0.92
            trace.append(f'step{step}: prompt_injection_isolation')
            reason = _grounded_reason(safety_signals, RiskCategory.PROMPT_INJECTION.value, action, msg_type)

    # ----------------------------------------------------------------
    # PRIORITY 4 — DANGEROUS CONTENT CONSTRAINTS
    # ----------------------------------------------------------------
    step += 1
    # Never allow scam/spam to notify
    if msg_type in ('scam', 'spam') and action == 'notify':
        overrides.append(ExecutionTrace(step, f'safety_override_{msg_type}_downgrade', action, msg_type,
                                         'mute', msg_type, f'Type {msg_type} cannot have action notify.'))
        action = 'mute'
        override_applied = True
        override_code = f'safety_{msg_type}_downgrade'
        trace.append(f'step{step}: {msg_type}_notify_downgrade')

    # Suspicious payment without legitimate context
    if (safety_signals.payment_destination_trust == 'suspicious' and
            safety_signals.payment_request and action == 'notify'):
        overrides.append(ExecutionTrace(step, 'payment_risk_constraint', action, msg_type,
                                         'mute', 'payment', 'Suspicious payment destination with no verified context.'))
        action = 'mute'
        msg_type = 'payment'
        override_applied = True
        confidence_ceiling = 0.85
        trace.append(f'step{step}: payment_risk_constraint')
        reason = _grounded_reason(safety_signals, RiskCategory.PAYMENT_RISK.value, action, msg_type)

    # Impersonation signal
    if safety_signals.impersonation_signal and action == 'notify':
        overrides.append(ExecutionTrace(step, 'impersonation_constraint', action, msg_type,
                                         'mute', 'scam', 'Unverified authority claim detected.'))
        action = 'mute'
        msg_type = 'scam'
        override_applied = True
        trace.append(f'step{step}: impersonation_constraint')
        reason = _grounded_reason(safety_signals, RiskCategory.IMPERSONATION_RISK.value, action, msg_type)

    # ----------------------------------------------------------------
    # PRIORITY 5 — LEGITIMATE IMMEDIATE NEED (protect genuine urgency)
    # ----------------------------------------------------------------
    step += 1
    if not override_applied and safety_signals.concrete_deadline:
        # Protect legitimate urgent notify — only if no safety override
        if (safety_signals.trusted_sender_context or
                deterministic_signals.get('sender_is_group_admin')) and not safety_signals.suspicious_link:
            if action in ('digest', 'mute') and msg_type not in ('scam', 'spam'):
                overrides.append(ExecutionTrace(step, 'legitimate_urgency_protect', action, msg_type,
                                                 'notify', 'urgent',
                                                 'Concrete deadline from trusted contact preserved.'))
                action = 'notify'
                msg_type = 'urgent'
                override_applied = True
                trace.append(f'step{step}: legitimate_urgency_protect')
                reason = _grounded_reason(safety_signals, 'NONE', action, msg_type)

    # ----------------------------------------------------------------
    # PRIORITY 6 — USER-SPECIFIC RELEVANCE
    # ----------------------------------------------------------------
    step += 1
    # Opted-out promotion → mute
    if (deterministic_signals.get('user_opted_out') and
            deterministic_signals.get('contains_promotion_language') and
            action == 'notify'):
        overrides.append(ExecutionTrace(step, 'opted_out_promotion_downgrade', action, msg_type,
                                         'mute', 'promotion', 'User has opted out of this sender.'))
        action = 'mute'
        msg_type = 'promotion'
        override_applied = True
        trace.append(f'step{step}: opted_out_promotion_downgrade')
        reason = _grounded_reason(safety_signals, RiskCategory.PROMOTION_UNWANTED.value, action, msg_type)

    # ----------------------------------------------------------------
    # PRIORITY 7 — QUIET HOURS / MUTE STATE
    # ----------------------------------------------------------------
    step += 1
    if (deterministic_signals.get('quiet_hours_active') and
            action == 'notify' and msg_type not in ('urgent', 'event')):
        overrides.append(ExecutionTrace(step, 'quiet_hours_downgrade', action, msg_type,
                                         'digest', msg_type, 'Quiet hours: non-urgent notify downgraded.'))
        action = 'digest'
        override_applied = True
        confidence_ceiling = min(confidence_ceiling, 0.85)
        trace.append(f'step{step}: quiet_hours_downgrade')

    # ----------------------------------------------------------------
    # PRIORITY 8 — PROMOTION AND LOW-VALUE POLICY
    # ----------------------------------------------------------------
    step += 1
    if (safety_signals.promotion_signal and action == 'notify' and
            not deterministic_signals.get('user_opted_in') and
            not safety_signals.concrete_deadline):
        overrides.append(ExecutionTrace(step, 'promo_notify_downgrade', action, msg_type,
                                         'digest', 'promotion', 'Promotional content without opt-in.'))
        action = 'digest'
        msg_type = 'promotion'
        override_applied = True
        trace.append(f'step{step}: promo_notify_downgrade')

    # ----------------------------------------------------------------
    # PRIORITY 9 — MODEL/BASELINE PROPOSAL (already in action/msg_type)
    # ----------------------------------------------------------------
    # Model proposal is the starting point; overrides above constrain it.
    step += 1
    trace.append(f'step{step}: model_proposal_accepted' if not override_applied else
                 f'step{step}: model_proposal_constrained')

    # ----------------------------------------------------------------
    # PRIORITY 10 — CONFIDENCE CALIBRATION
    # ----------------------------------------------------------------
    # Media failure penalty
    if media_quality == 'failed' and action in ('notify', 'digest'):
        confidence_ceiling = min(confidence_ceiling, 0.70)
        safety_signals.uncertainties.append('confidence_penalized_media_failure')

    # Language uncertainty penalty
    if safety_signals.detected_language == 'unknown':
        confidence_ceiling = min(confidence_ceiling, 0.80)
        safety_signals.uncertainties.append('confidence_penalized_language_unknown')

    # Conflicting signals reduce ceiling
    if safety_signals.conflicting_signals:
        confidence_ceiling = min(confidence_ceiling, 0.82)
        safety_signals.uncertainties.append('confidence_penalized_conflicting_signals')

    # Provider fallback penalty
    if deterministic_signals.get('llm_fallback_active'):
        confidence_ceiling = min(confidence_ceiling, 0.75)

    # Credential warning (legitimate safety advice) — preserve higher confidence for notify
    if safety_signals.credential_warning and action == 'notify':
        confidence_ceiling = min(0.88, confidence_ceiling)

    # ----------------------------------------------------------------
    # REASON CONSISTENCY CHECK
    # ----------------------------------------------------------------
    final_reason = reason
    if not final_reason or not final_reason.strip():
        final_reason = _grounded_reason(safety_signals, risk_cat, action, msg_type)

    # Evidence consistency: if reason mentions history but evidence is none
    if proposed_evidence_ids == ['none'] and (
            'history' in final_reason.lower() or 'previously' in final_reason.lower()):
        final_reason = ('Routed based on content patterns and sender context '
                        'without specific historical evidence.')
        trace.append('reason_evidence_consistency_fix')

    # Build allowed evidence IDs (already validated upstream by validate_evidence_safety)
    allowed_evidence_ids = proposed_evidence_ids if proposed_evidence_ids else ['none']

    return PolicyDecision(
        final_action=action,
        final_message_type=msg_type,
        override_applied=override_applied,
        override_reason_code=override_code,
        confidence_ceiling=confidence_ceiling,
        confidence_floor=confidence_floor,
        required_reason_signals=list(safety_signals.conflicting_signals),
        allowed_evidence_ids=allowed_evidence_ids,
        trace=trace,
        safety_signals=safety_signals,
    ), final_reason
