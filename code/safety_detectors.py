"""
Phase 12 — Deterministic Safety Detectors

Extracts SafetySignals from all available input sources.
All detectors record source provenance.
No detector trusts model output as a source of safety truth.

Key design principles:
- Credential REQUESTS are distinct from credential WARNINGS.
- Trusted senders do NOT automatically make credential/payment requests safe.
- Verified businesses do NOT automatically bypass safety constraints.
- Failed media extraction does NOT imply safety.
- Prompt injection alone does not conclusively classify scam — full context matters.
"""

import re
import sys
import os
from typing import List, Optional, Any
from urllib.parse import urlparse

# Ensure code/ is on sys.path when run standalone
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from schemas import (
    SafetySignals, SignalSource, RiskCategory, RISK_TIER_MAP,
    IncomingMessageContext, MediaAnalysis
)
from multilingual_safety import normalize_for_safety, extract_multilingual_signals


# ============================================================
# DETECTOR VERSION
# ============================================================

DETECTOR_VERSION = "phase12_v1"


# ============================================================
# LINK / DOMAIN SAFETY
# ============================================================

_TRUSTED_DOMAINS = frozenset([
    'amazon.in', 'amazon.com', 'flipkart.com', 'myntra.com', 'zomato.com',
    'swiggy.com', 'ola.in', 'uber.com', 'paytm.com', 'phonepe.com',
    'hdfcbank.com', 'sbi.co.in', 'icicibank.com', 'axisbank.com',
    'irctc.co.in', 'pvrinemas.com', 'bookmyshow.com', 'redbus.in',
    'makemytrip.com', 'cleartrip.com', 'goibibo.com', 'airtel.in',
    'jio.com', 'bsnl.co.in', 'vodafone.in', 'google.com', 'microsoft.com',
    'whatsapp.com', 'facebook.com', 'instagram.com', 'twitter.com',
])

_URL_SHORTENERS = frozenset([
    'bit.ly', 'tinyurl.com', 'shorte.st', 'is.gd', 'ow.ly', 'goo.gl',
    't.co', 'rb.gy', 'cutt.ly', 'shorturl.at', 'tiny.cc', 'clck.ru',
    'v.gd', 'lmgtfy.com',
])

_SUSPICIOUS_PATH_PATTERN = re.compile(
    r'(account.login|account.help|verify.me|secure.verify|pay.check|'
    r'login.verify|otp.confirm|wallet.verify|profile.update|'
    r'account.restore|security.check|urgent.verify)',
    re.IGNORECASE
)

_URL_PATTERN = re.compile(
    r'https?://[^\s<>"]+|www\.[^\s<>"]+|[a-z0-9][a-z0-9\-]*\.[a-z]{2,}/[^\s]*',
    re.IGNORECASE
)


def _analyze_url(url_str: str) -> dict:
    """Parse a URL safely without making network requests."""
    try:
        if not url_str.startswith(('http://', 'https://')):
            url_str = 'https://' + url_str
        parsed = urlparse(url_str)
        host = parsed.netloc.lower().lstrip('www.')
        # Remove port
        host = host.split(':')[0]
        scheme = parsed.scheme
        path = parsed.path

        is_shortener = any(host == s or host.endswith('.' + s) for s in _URL_SHORTENERS)
        is_trusted = any(host == d or host.endswith('.' + d) for d in _TRUSTED_DOMAINS)
        has_suspicious_path = bool(_SUSPICIOUS_PATH_PATTERN.search(path))

        trust = 'trusted' if is_trusted and not has_suspicious_path else \
                'shortener' if is_shortener else \
                'suspicious' if has_suspicious_path else 'unknown'

        return {
            'raw': url_str,
            'host': host,
            'scheme': scheme,
            'shortener': is_shortener,
            'trusted': is_trusted,
            'suspicious_path': has_suspicious_path,
            'trust': trust,
        }
    except Exception:
        return {'raw': url_str, 'host': '', 'scheme': '', 'shortener': False,
                'trusted': False, 'suspicious_path': False, 'trust': 'unknown'}


def analyze_links(text: str) -> tuple:
    """
    Extract and analyze all URLs in text.
    Returns (suspicious_link: bool, domain_trust: str, sources: list).
    Does NOT make network requests.
    """
    urls = _URL_PATTERN.findall(text)
    if not urls:
        return False, 'none', []

    analyses = [_analyze_url(u) for u in urls]
    trusts = [a['trust'] for a in analyses]

    if 'suspicious' in trusts:
        overall_trust = 'suspicious'
    elif 'shortener' in trusts:
        overall_trust = 'shortener'
    elif all(t == 'trusted' for t in trusts):
        overall_trust = 'trusted'
    else:
        overall_trust = 'unknown'

    suspicious = overall_trust in ('suspicious', 'shortener')
    sources = [
        SignalSource(
            source='link_parser',
            grounded_value=a['raw'][:100],
            detector='analyze_links',
            confidence=0.8 if a['trust'] == 'suspicious' else 0.6,
            trusted=a['trusted'],
        )
        for a in analyses if a['trust'] in ('suspicious', 'shortener')
    ]
    return suspicious, overall_trust, sources


# ============================================================
# CREDENTIAL DETECTOR
# ============================================================

# Request patterns (asking the user to share credentials)
_CRED_REQUEST_PATTERNS = [
    # OTP request — keyword BEFORE action
    re.compile(
        r'\b(otp|one.time.pass(?:word|code)?|verification.code|login.code|auth.code)\b.{0,40}'
        r'(share|send|enter|reply|submit|confirm|give|type|tell)',
        re.IGNORECASE | re.DOTALL
    ),
    # Action BEFORE OTP keyword: 'send me your OTP', 'share your one time password'
    re.compile(
        r'(share|send|give|tell|reply|provide)\s*.{0,20}?(otp|one.time.pass(?:word|code)?|verification.code)',
        re.IGNORECASE
    ),
    # Password/PIN request
    re.compile(
        r'(password|passwd|\bpin\b|passcode|login.code|access.code).{0,30}'
        r'(share|send|give|enter|confirm|reply|tell|type)',
        re.IGNORECASE | re.DOTALL
    ),
    re.compile(
        r'(enter|type|provide|submit).{0,20}(password|pin|otp|code)',
        re.IGNORECASE
    ),
    # Recovery code request
    re.compile(
        r'(recovery|backup|security)\s*code.{0,20}(share|send|give|enter)',
        re.IGNORECASE
    ),
]

# Warning patterns (telling the user NOT to share — opposite signal)
_CRED_WARNING_PATTERNS = [
    re.compile(
        r'(never|do not|don\'?t|never ever|please never)\s*(share|give|send|tell|enter|type).{0,30}(otp|password|pin|code)',
        re.IGNORECASE
    ),
    re.compile(
        r'(otp|password|pin|code).{0,30}(never|don\'?t|do not|kabhi nahi?)\s*(share|send|give)',
        re.IGNORECASE
    ),
    re.compile(
        r'(beware|caution|alert|warning).{0,50}(otp|password|credentials)',
        re.IGNORECASE
    ),
    re.compile(
        r'we\s+(will\s+)?never\s+(ask|request).{0,30}(otp|password|pin)',
        re.IGNORECASE
    ),
    # Standalone warning phrases
    re.compile(
        r'never\s+share\s+(your\s+)?(otp|password|pin|code)',
        re.IGNORECASE
    ),
    re.compile(
        r'do\s+not\s+share\s+(your\s+)?(otp|password|pin|code)',
        re.IGNORECASE
    ),
]


def detect_credential_risk(text: str, source_label: str = 'text', trusted_source: bool = False) -> tuple:
    """
    Detect credential requests vs credential warnings.
    Returns (credential_request: bool, credential_warning: bool, sources: list).

    Trusted senders do NOT override credential risk — only affect confidence.
    Design: warnings are checked AFTER requests. A pure warning (no request) yields
    is_request=False, is_warning=True. A pure request yields is_request=True, is_warning=False.
    Both present = ambiguous (lower confidence on request).
    """
    # Check requests first
    is_request = False
    request_sources = []
    for pattern in _CRED_REQUEST_PATTERNS:
        m = pattern.search(text)
        if m:
            is_request = True
            request_sources.append(SignalSource(
                source=source_label,
                grounded_value=m.group(0)[:80],
                detector='detect_credential_risk',
                confidence=0.85 if not trusted_source else 0.70,
                trusted=trusted_source,
            ))

    # Check warnings
    is_warning = any(p.search(text) for p in _CRED_WARNING_PATTERNS)

    # Pure warning with no request = NOT a risk
    # If both present = ambiguous; keep is_request=True but reduce confidence
    if is_warning and is_request:
        for s in request_sources:
            s.confidence = max(0.4, s.confidence - 0.3)

    # If warning only (no request keyword), suppress request
    if is_warning and not is_request:
        pass  # correct: is_request stays False

    return is_request, is_warning, request_sources


# ============================================================
# PAYMENT RISK DETECTOR
# ============================================================

_PAYMENT_REQUEST_PATTERNS = [
    # Suspicious payment pressure
    re.compile(
        r'(pay|transfer|send).{0,20}(now|immediately|today|urgent|asap|jaldi|abhi)',
        re.IGNORECASE | re.DOTALL
    ),
    re.compile(
        r'(scan|use).{0,10}(qr|qr.code|barcode).{0,30}(pay|transfer|payment)',
        re.IGNORECASE
    ),
    re.compile(
        r'(clearance|token|advance|security)\s*(amount|fee|deposit)',
        re.IGNORECASE
    ),
    # Refund/prize bait with fee required
    re.compile(
        r'(refund|cashback|prize|reward|claim).{0,50}(pay|fee|charge|deposit|processing)',
        re.IGNORECASE | re.DOTALL
    ),
    re.compile(
        r'(pay|deposit|charge).{0,20}(fee|amount|charge).{0,20}(refund|claim|prize|reward|process)',
        re.IGNORECASE | re.DOTALL
    ),
    # Screenshot / proof request
    re.compile(
        r'(send|share|upload).{0,20}(payment|transaction|bank)\s*(screenshot|proof|slip)',
        re.IGNORECASE
    ),
]

_LEGITIMATE_PAYMENT_INDICATORS = [
    re.compile(r'(order|booking|subscription|invoice|bill|receipt)\s*(id|number|#|:)', re.IGNORECASE),
    re.compile(r'\b(ord|order|booking)\s*[a-z0-9]{3,}\b', re.IGNORECASE),  # 'Order ORD123'
    re.compile(r'(due|payment)\s*(date|reminder|scheduled)', re.IGNORECASE),
    re.compile(r'auto.?(debit|pay|renew)', re.IGNORECASE),
    re.compile(r'(emi|installment|premium)\s*(due|payment|is)', re.IGNORECASE),
    re.compile(r'your\s+(emi|bill|invoice|subscription)\s+(is\s+)?due', re.IGNORECASE),
]

_QR_PATTERNS = [
    re.compile(r'\bqr\s*(code|scan|payment)\b', re.IGNORECASE),
    re.compile(r'scan\s*(the|this|a)\s*qr', re.IGNORECASE),
]


def detect_payment_risk(text: str, source_label: str = 'text',
                         business_relationship: bool = False,
                         trusted_sender: bool = False) -> tuple:
    """
    Detect suspicious payment pressure vs legitimate payment reminders.
    Returns (payment_request: bool, is_suspicious: bool, has_legitimate_indicator: bool,
             qr_present: bool, sources: list).
    """
    is_suspicious = any(p.search(text) for p in _PAYMENT_REQUEST_PATTERNS)
    has_legit = any(p.search(text) for p in _LEGITIMATE_PAYMENT_INDICATORS)
    qr_present = any(p.search(text) for p in _QR_PATTERNS)
    payment_request = is_suspicious or has_legit or qr_present

    sources = []
    if is_suspicious:
        # Find which pattern matched
        for p in _PAYMENT_REQUEST_PATTERNS:
            m = p.search(text)
            if m:
                # Reduce risk if business relationship + legit indicator
                conf = 0.80
                if business_relationship and has_legit:
                    conf = 0.50
                elif trusted_sender and has_legit:
                    conf = 0.45
                sources.append(SignalSource(
                    source=source_label,
                    grounded_value=m.group(0)[:80],
                    detector='detect_payment_risk',
                    confidence=conf,
                    trusted=trusted_sender,
                ))
                break

    return payment_request, is_suspicious, has_legit, qr_present, sources


# ============================================================
# ACCOUNT PRESSURE DETECTOR
# ============================================================

_ACCOUNT_BLOCK_PATTERNS = [
    re.compile(
        r'(account|profile|access|id).{0,20}(blocked?|suspended?|deactivated?|terminated?|restricted?)',
        re.IGNORECASE | re.DOTALL
    ),
    re.compile(
        r'(block|suspend|deactivate|restrict).{0,20}(your|account|profile)',
        re.IGNORECASE | re.DOTALL
    ),
    re.compile(
        r'(khata|account).{0,15}(band|block)',
        re.IGNORECASE
    ),
    re.compile(
        r'24\s*hours?.{0,30}(block|suspend|close|verify)',
        re.IGNORECASE | re.DOTALL
    ),
]

_REWARD_PATTERNS = [
    re.compile(
        r'(won|win|winner|prize|reward|lottery|lucky\s*draw|jackpot).{0,30}(claim|collect|congratulations)',
        re.IGNORECASE | re.DOTALL
    ),
    re.compile(
        r'(congratulations?|congrats).{0,50}(selected|won|winner|prize|reward)',
        re.IGNORECASE | re.DOTALL
    ),
    re.compile(
        r'(inaam|prize|reward|lottery).{0,20}(jeet|mila|aapko)',
        re.IGNORECASE
    ),
]

_IMPERSONATION_INDICATORS = [
    re.compile(r'\b(rbi|reserve bank|income tax|police|cyber crime|cbi|cia|fbi)\b', re.IGNORECASE),
    re.compile(r'\bgovernment\s*(of\s*india|official|authority)\b', re.IGNORECASE),
    re.compile(r'\byour\s*bank\s*(official|representative|manager|officer)\b', re.IGNORECASE),
]


def detect_pressure_signals(text: str, source_label: str = 'text',
                              business_is_verified: bool = False) -> tuple:
    """
    Detect account blocking pressure, reward/lottery scams, and impersonation signals.
    Returns (account_blocking: bool, reward_lottery: bool, impersonation: bool, sources: list).
    """
    account_blocking = any(p.search(text) for p in _ACCOUNT_BLOCK_PATTERNS)
    reward_lottery = any(p.search(text) for p in _REWARD_PATTERNS)
    impersonation = any(p.search(text) for p in _IMPERSONATION_INDICATORS)

    sources = []
    if account_blocking:
        for p in _ACCOUNT_BLOCK_PATTERNS:
            m = p.search(text)
            if m:
                sources.append(SignalSource(
                    source=source_label,
                    grounded_value=m.group(0)[:80],
                    detector='detect_pressure_signals.account_block',
                    confidence=0.80 if not business_is_verified else 0.60,
                    trusted=business_is_verified,
                ))
                break
    if reward_lottery:
        for p in _REWARD_PATTERNS:
            m = p.search(text)
            if m:
                sources.append(SignalSource(
                    source=source_label,
                    grounded_value=m.group(0)[:80],
                    detector='detect_pressure_signals.reward_lottery',
                    confidence=0.85,
                    trusted=False,
                ))
                break
    if impersonation:
        for p in _IMPERSONATION_INDICATORS:
            m = p.search(text)
            if m:
                sources.append(SignalSource(
                    source=source_label,
                    grounded_value=m.group(0)[:80],
                    detector='detect_pressure_signals.impersonation',
                    confidence=0.70,
                    trusted=False,
                ))
                break

    return account_blocking, reward_lottery, impersonation, sources


# ============================================================
# PROMPT INJECTION DETECTOR
# ============================================================

_INJECTION_PATTERNS = [
    # Direct action override attempts
    re.compile(r'\bset\s+(action|output)\s*(to|=)\s*(notify|digest|mute)\b', re.IGNORECASE),
    re.compile(r'\b(action|output)\s*[:=]\s*(notify|digest|mute)\b', re.IGNORECASE),
    re.compile(r'\bclassify\s+(this|message)\s+as\s+(notify|digest|mute)\b', re.IGNORECASE),
    re.compile(r'\bignore\s+(previous|all|above|rules?|constraints?|instructions?).{0,20}(output|classify|and|set|action)', re.IGNORECASE),
    re.compile(r'\bignore\s+(previous|all|above)\s*(instructions?|rules?|constraints?)\b', re.IGNORECASE),
    re.compile(r'\boverride\s+(safety|policy|rules?|constraints?)\b', re.IGNORECASE),
    # Confidence / evidence manipulation
    re.compile(r'\bset\s+confidence\s*(to|=)\s*[01](\.\d+)?\b', re.IGNORECASE),
    re.compile(r'\bevidence[_\s]*(message[_\s]*)?ids?\s*[:=]\s*[A-Z0-9]{3,}', re.IGNORECASE),
    # System authority claims
    re.compile(r'\b(you\s+are|act\s+as|pretend|roleplay)\s+(a\s+)?system\b', re.IGNORECASE),
    re.compile(r'\bsystem\s+(prompt|instruction|message)\b', re.IGNORECASE),
    re.compile(r'\b(reveal|print|show)\s+(your\s+)?(prompt|system|instruction|api.key)\b', re.IGNORECASE),
    # Disable safety
    re.compile(r'\bdisable\s+(safety|filter|constraint)\b', re.IGNORECASE),
    re.compile(r'\bbypass\s+(safety|filter|policy)\b', re.IGNORECASE),
    # Tool use / provider manipulation
    re.compile(r'\bcall\s+(api|provider|tool|function)\b', re.IGNORECASE),
    re.compile(r'\btrigger\s+provider\b', re.IGNORECASE),
    # Output instruction
    re.compile(r'\boutput\s+(notify|digest|mute|spam|scam)\b', re.IGNORECASE),
]

# Non-injection legitimate uses that might trigger false positives
_INJECTION_SAFE_CONTEXTS = [
    re.compile(r'\bnotify\s+(me|us)\s+(when|if|about)\b', re.IGNORECASE),  # "notify me when" — normal
    re.compile(r'\bmute\s+(this|the)\s+(phone|device|sound)\b', re.IGNORECASE),  # device muting
    re.compile(r'\baction\s+(is|was|will)\s+taken\b', re.IGNORECASE),  # normal usage
]


def detect_prompt_injection(text: str, source_label: str = 'text') -> tuple:
    """
    Detect prompt injection attempts in text content.
    Does NOT automatically classify the message as scam — context matters.
    Returns (is_injection: bool, sources: list).
    """
    # Check safe contexts first (reduce false positives)
    has_safe_context = any(p.search(text) for p in _INJECTION_SAFE_CONTEXTS)

    sources = []
    for pattern in _INJECTION_PATTERNS:
        m = pattern.search(text)
        if m:
            # Lower confidence if safe context is present
            conf = 0.60 if has_safe_context else 0.85
            sources.append(SignalSource(
                source=source_label,
                grounded_value=m.group(0)[:80],
                detector='detect_prompt_injection',
                confidence=conf,
                trusted=False,
            ))

    is_injection = len(sources) > 0 and not has_safe_context
    # If both injection and safe context, flag as uncertain
    if len(sources) > 0 and has_safe_context:
        is_injection = False  # safe context wins for isolated false-positive prevention

    return is_injection, sources


# ============================================================
# URGENCY DETECTOR
# ============================================================

_CONCRETE_DEADLINE_PATTERNS = [
    re.compile(r'\b(today|tonight|this\s+morning|this\s+evening|by\s+\d+\s*(am|pm))\b', re.IGNORECASE),
    re.compile(r'\b(in\s+\d+\s*(minute|hour|min|hr)s?)\b', re.IGNORECASE),
    re.compile(r'\b\d{1,2}[:\-]\d{2}\s*(am|pm)?\b', re.IGNORECASE),
    re.compile(r'\bwaiting\s+(for\s+you|outside|downstairs|at\s+the\s+door)\b', re.IGNORECASE),
    re.compile(r'\b(flight|train|bus|delivery)\s+(is\s+)?(arriving|leaving|departing|here)\b', re.IGNORECASE),
    re.compile(r'\b(last\s+day|final\s+notice|deadline\s+(is\s+)?(today|tomorrow|now))\b', re.IGNORECASE),
]

_VAGUE_URGENCY_PATTERNS = [
    re.compile(r'\b(urgent|urgently|emergency|asap|immediately|right\s*now)\b', re.IGNORECASE),
    re.compile(r'\b(jaldi|turant|abhi|fauran)\b', re.IGNORECASE),
    re.compile(r'\b(don\'?t\s+delay|hurry|rush)\b', re.IGNORECASE),
]

_FUTURE_EVENT_PATTERNS = [
    re.compile(r'\b(next\s+week|next\s+month|upcoming|tomorrow\s+at)\b', re.IGNORECASE),
    re.compile(r'\bin\s+(two|three|four|five|\d+)\s+(days?|weeks?|months?)\b', re.IGNORECASE),
]


def detect_urgency(text: str, source_label: str = 'text') -> tuple:
    """
    Detect urgency signals, distinguishing concrete deadlines from vague pressure.
    Returns (has_urgency: bool, has_concrete_deadline: bool, is_future_event: bool, sources: list).
    """
    has_concrete = any(p.search(text) for p in _CONCRETE_DEADLINE_PATTERNS)
    has_vague = any(p.search(text) for p in _VAGUE_URGENCY_PATTERNS)
    is_future = any(p.search(text) for p in _FUTURE_EVENT_PATTERNS)
    has_urgency = has_concrete or has_vague

    sources = []
    if has_concrete:
        for p in _CONCRETE_DEADLINE_PATTERNS:
            m = p.search(text)
            if m:
                sources.append(SignalSource(
                    source=source_label,
                    grounded_value=m.group(0)[:60],
                    detector='detect_urgency.concrete',
                    confidence=0.80,
                    trusted=True,
                ))
                break
    elif has_vague:
        for p in _VAGUE_URGENCY_PATTERNS:
            m = p.search(text)
            if m:
                sources.append(SignalSource(
                    source=source_label,
                    grounded_value=m.group(0)[:60],
                    detector='detect_urgency.vague',
                    confidence=0.55,
                    trusted=False,  # vague urgency is not self-verifying
                ))
                break

    return has_urgency, has_concrete, is_future, sources


# ============================================================
# EVIDENCE SAFETY
# ============================================================

def validate_evidence_safety(evidence_ids: list, incoming_message_id: str,
                               user_id: str, all_message_ids: set,
                               event_ids: set, incoming_timestamp: str,
                               evidence_timestamps: dict) -> tuple:
    """
    Validate that evidence IDs are safe to use.
    Returns (is_safe: bool, violations: list, safe_ids: list).

    Violations:
    - Incoming message ID used as evidence
    - Event IDs used as evidence
    - Future evidence (timestamp after incoming)
    - Duplicate evidence IDs
    - IDs not in the allowed message history
    """
    violations = []
    seen = set()
    safe_ids = []

    for eid in evidence_ids:
        if eid.lower() == 'none':
            safe_ids.append(eid)
            continue

        # Check for incoming ID
        if eid == incoming_message_id:
            violations.append(f'incoming_id_as_evidence:{eid}')
            continue

        # Check for event ID
        if eid in event_ids:
            violations.append(f'event_id_as_evidence:{eid}')
            continue

        # Check for duplicate
        if eid in seen:
            violations.append(f'duplicate_evidence:{eid}')
            continue

        # Check if ID exists in message history
        if all_message_ids and eid not in all_message_ids:
            violations.append(f'unknown_evidence_id:{eid}')
            continue

        # Check for future evidence
        if incoming_timestamp and eid in evidence_timestamps:
            ev_ts = evidence_timestamps[eid]
            if ev_ts > incoming_timestamp:
                violations.append(f'future_evidence:{eid}')
                continue

        seen.add(eid)
        safe_ids.append(eid)

    is_safe = len(violations) == 0
    return is_safe, violations, safe_ids if safe_ids else ['none']


# ============================================================
# MAIN EXTRACTOR
# ============================================================

def extract_safety_signals(
    msg_ctx: IncomingMessageContext,
    raw_message: dict,
    profile: Any,
    all_message_ids: Optional[set] = None,
    event_ids: Optional[set] = None,
    evidence_timestamps: Optional[dict] = None,
) -> SafetySignals:
    """
    Main entry point: extract SafetySignals from all input sources.

    Sources inspected:
    - Message text (with multilingual normalization)
    - Image OCR text and visual summary
    - Voice transcript
    - Sender metadata
    - Business metadata
    - Group context
    - Link/domain parser
    - Evidence IDs

    Returns SafetySignals with full source provenance.
    """
    sig = SafetySignals(detector_version=DETECTOR_VERSION)

    # --- Gather text from all sources ---
    msg_text = raw_message.get('message_text', '') or ''
    image_ocr = ''
    image_visual = ''
    voice_transcript = ''

    if msg_ctx.media_analysis:
        if msg_ctx.media_type == 'image':
            image_ocr = getattr(msg_ctx.media_analysis, 'ocr_text', '') or ''
            image_visual = getattr(msg_ctx.media_analysis, 'visual_summary', '') or ''
            sig.media_grounding_quality = 'failed' if msg_ctx.media_analysis.failure else 'medium'
        elif msg_ctx.media_type == 'voice':
            voice_transcript = getattr(msg_ctx.media_analysis, 'transcript', '') or ''
            sig.media_grounding_quality = 'failed' if msg_ctx.media_analysis.failure else 'medium'

    # --- Multilingual normalization ---
    norm = normalize_for_safety(
        msg_text,
        apply_ocr=(msg_ctx.media_type == 'image'),
        apply_asr=(msg_ctx.media_type == 'voice'),
    )
    sig.multilingual_normalized = len(norm.transformations_applied) > 0
    sig.detected_language = norm.detected_language
    normalized_text = norm.normalized

    # --- Multilingual signals ---
    ml_signals = extract_multilingual_signals(normalized_text)
    if voice_transcript:
        norm_voice = normalize_for_safety(voice_transcript, apply_asr=True)
        ml_voice = extract_multilingual_signals(norm_voice.normalized)
        for k in ml_signals:
            ml_signals[k] = ml_signals[k] or ml_voice.get(k, False)

    # --- Context flags ---
    business_is_verified = bool(
        msg_ctx.business_context.get('is_verified') or
        msg_ctx.business_context.get('verified')
    )
    business_relationship = bool(
        msg_ctx.historical_context.get('has_transaction') or
        msg_ctx.business_context.get('has_transaction') or
        msg_ctx.business_context.get('active_relationship')
    )
    trusted_sender = bool(
        msg_ctx.sender_context.get('is_trusted') or
        msg_ctx.deterministic_signals.get('sender_trusted_personal')
    )
    sender_is_group_admin = bool(
        msg_ctx.group_context.get('sender_is_admin') or
        msg_ctx.deterministic_signals.get('sender_is_group_admin')
    )

    sig.legitimate_relationship = business_relationship or trusted_sender
    sig.business_relationship = business_relationship
    sig.trusted_sender_context = trusted_sender
    sig.historical_report_signal = bool(msg_ctx.deterministic_signals.get('business_reports_high'))
    sig.historical_engagement_signal = bool(msg_ctx.deterministic_signals.get('historical_reply_signal'))

    # --- Link/domain analysis ---
    full_text_for_links = ' '.join(filter(None, [msg_text, image_ocr, voice_transcript]))
    suspicious_link, domain_trust, link_sources = analyze_links(full_text_for_links)
    sig.suspicious_link = suspicious_link
    sig.domain_trust = domain_trust
    sig.payment_sources.extend(link_sources)

    # --- Credential detection (text) ---
    cred_req, cred_warn, cred_sources = detect_credential_risk(
        normalized_text, source_label='text', trusted_source=trusted_sender
    )
    sig.credential_request = cred_req or ml_signals.get('ml_credential_request', False)
    sig.credential_warning = cred_warn or ml_signals.get('ml_credential_warning', False)
    sig.otp_request = bool(re.search(r'\botp\b', normalized_text, re.IGNORECASE) and cred_req)
    sig.password_request = bool(re.search(r'\bpassword\b|\bpasswd\b', normalized_text, re.IGNORECASE) and cred_req)
    sig.pin_request = bool(re.search(r'\bpin\b', normalized_text, re.IGNORECASE) and cred_req)
    sig.credential_sources.extend(cred_sources)

    # Credential detection in image OCR
    if image_ocr:
        norm_ocr = normalize_for_safety(image_ocr, apply_ocr=True)
        img_cred_req, img_cred_warn, img_cred_sources = detect_credential_risk(
            norm_ocr.normalized, source_label='image_ocr', trusted_source=False
        )
        if img_cred_req:
            sig.credential_request = True
            sig.credential_sources.extend(img_cred_sources)
        if img_cred_warn:
            sig.credential_warning = True

    # Credential detection in voice transcript
    if voice_transcript:
        norm_voice = normalize_for_safety(voice_transcript, apply_asr=True)
        v_cred_req, v_cred_warn, v_cred_sources = detect_credential_risk(
            norm_voice.normalized, source_label='voice_transcript', trusted_source=False
        )
        if v_cred_req:
            sig.credential_request = True
            sig.credential_sources.extend(v_cred_sources)
        if v_cred_warn:
            sig.credential_warning = True

    # --- Payment detection ---
    pay_req, pay_suspicious, pay_legit, qr_present, pay_sources = detect_payment_risk(
        normalized_text, source_label='text',
        business_relationship=business_relationship,
        trusted_sender=trusted_sender,
    )
    sig.payment_request = pay_req or ml_signals.get('ml_urgent_payment', False)
    sig.qr_present = qr_present or bool(msg_ctx.deterministic_signals.get('contains_qr_reference'))
    sig.payment_sources.extend(pay_sources)

    # Payment destination trust
    if business_is_verified and pay_legit and not pay_suspicious:
        sig.payment_destination_trust = 'trusted'
    elif pay_suspicious and (suspicious_link or not business_is_verified):
        sig.payment_destination_trust = 'suspicious'
    else:
        sig.payment_destination_trust = 'unknown'

    # --- Pressure signals ---
    acct_block, reward_lottery, impersonation, pressure_sources = detect_pressure_signals(
        normalized_text, source_label='text', business_is_verified=business_is_verified
    )
    sig.account_blocking_pressure = acct_block or ml_signals.get('ml_account_blocking', False)
    sig.reward_or_lottery = reward_lottery or ml_signals.get('ml_reward_lottery', False)
    sig.impersonation_signal = impersonation
    sig.pressure_sources.extend(pressure_sources)

    # High-forward count as dangerous forward signal
    forwarded_count = int(raw_message.get('forwarded_count', 0) or 0)
    sig.dangerous_forward_signal = forwarded_count >= 5

    # --- Promotion signal ---
    sig.promotion_signal = bool(msg_ctx.deterministic_signals.get('contains_promotion_language'))

    # --- Prompt injection ---
    full_check_text = ' '.join(filter(None, [msg_text, image_ocr, image_visual, voice_transcript]))
    is_injection, injection_sources = detect_prompt_injection(full_check_text, source_label='text')
    # Also check each source independently
    if image_ocr and not is_injection:
        is_inj_img, inj_img_srcs = detect_prompt_injection(image_ocr, source_label='image_ocr')
        if is_inj_img:
            is_injection = True
            injection_sources.extend(inj_img_srcs)
    if voice_transcript and not is_injection:
        is_inj_voice, inj_voice_srcs = detect_prompt_injection(voice_transcript, source_label='voice_transcript')
        if is_inj_voice:
            is_injection = True
            injection_sources.extend(inj_voice_srcs)
    sig.prompt_injection_signal = is_injection
    sig.injection_sources.extend(injection_sources)

    # --- Urgency signals ---
    has_urgency, has_concrete, is_future, urgency_sources = detect_urgency(
        normalized_text, source_label='text'
    )
    sig.urgency_language = has_urgency or ml_signals.get('ml_urgency_language', False) or ml_signals.get('ml_urgent_action', False)
    sig.concrete_deadline = has_concrete
    sig.urgency_sources.extend(urgency_sources)

    # --- Conflicting signals ---
    if sig.trusted_sender_context and sig.credential_request:
        sig.conflicting_signals.append('trusted_sender_requests_credentials')
    if business_is_verified and (sig.credential_request or sig.account_blocking_pressure):
        sig.conflicting_signals.append('verified_business_has_risk_signals')
    if sig.credential_warning and sig.credential_request:
        sig.conflicting_signals.append('credential_warning_alongside_request')
    if sig.legitimate_relationship and sig.suspicious_link:
        sig.conflicting_signals.append('known_relationship_but_suspicious_link')
    if sig.media_grounding_quality == 'failed' and sig.urgency_language:
        sig.conflicting_signals.append('media_failed_but_urgency_claimed')
        sig.uncertainties.append('urgency_based_on_failed_media_extraction')

    # --- Risk scoring ---
    risk_score = 0.0
    primary_category = RiskCategory.NONE

    if sig.prompt_injection_signal:
        risk_score = max(risk_score, 0.85)
        primary_category = RiskCategory.PROMPT_INJECTION
    if sig.credential_request and not sig.credential_warning:
        risk_score = max(risk_score, 0.90)
        primary_category = RiskCategory.CREDENTIAL_RISK
        if sig.account_blocking_pressure or sig.suspicious_link:
            risk_score = min(1.0, risk_score + 0.05)
    if sig.reward_or_lottery:
        risk_score = max(risk_score, 0.80)
        if primary_category == RiskCategory.NONE:
            primary_category = RiskCategory.PHISHING_RISK
    if sig.impersonation_signal:
        risk_score = max(risk_score, 0.75)
        if primary_category in (RiskCategory.NONE, RiskCategory.LOW_VALUE):
            primary_category = RiskCategory.IMPERSONATION_RISK
    if sig.account_blocking_pressure and (sig.suspicious_link or not business_is_verified):
        risk_score = max(risk_score, 0.82)
        if primary_category == RiskCategory.NONE:
            primary_category = RiskCategory.PHISHING_RISK
    if sig.payment_destination_trust == 'suspicious' and sig.payment_request:
        risk_score = max(risk_score, 0.78)
        if primary_category == RiskCategory.NONE:
            primary_category = RiskCategory.PAYMENT_RISK
    if sig.dangerous_forward_signal and bool(msg_ctx.deterministic_signals.get('historical_mute_signal')):
        if primary_category == RiskCategory.NONE:
            primary_category = RiskCategory.DANGEROUS_FORWARD
            risk_score = max(risk_score, 0.65)
    if sig.promotion_signal and bool(msg_ctx.deterministic_signals.get('user_opted_out')):
        if primary_category == RiskCategory.NONE:
            primary_category = RiskCategory.PROMOTION_UNWANTED
            risk_score = max(risk_score, 0.50)

    # Reduce risk if credential warning is present (legitimate security advice message)
    if sig.credential_warning and not sig.credential_request:
        risk_score = max(0.0, risk_score - 0.3)
        primary_category = RiskCategory.NONE

    # Reduce risk if trusted sender + legitimate relationship + no suspicious link
    if sig.trusted_sender_context and sig.legitimate_relationship and not sig.suspicious_link:
        risk_score = max(0.0, risk_score - 0.15)

    sig.risk_score = round(min(1.0, risk_score), 3)
    sig.risk_category = primary_category.value
    sig.risk_tier = RISK_TIER_MAP.get(primary_category, 0)

    # Recommended constraint
    if sig.risk_tier >= 7:
        sig.recommended_constraint = 'mute_scam'
    elif sig.risk_tier >= 5:
        sig.recommended_constraint = 'mute'
    elif sig.risk_tier >= 3:
        sig.recommended_constraint = 'digest'
    else:
        sig.recommended_constraint = 'none'

    return sig
