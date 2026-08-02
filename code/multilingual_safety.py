"""
Phase 12 — Multilingual Safety Normalization

Normalizes message text for defensive safety detection across:
- English
- Hindi (transliterated into Latin script)
- Hinglish (code-switched Hindi-English)
- Common OCR spacing/substitution artifacts
- Common ASR transcription variations

IMPORTANT: Normalization is for detection only.
- Original content is always preserved.
- Translation is NOT performed (original meaning retained).
- Detectors operate on the normalized form; reasons cite original content.
- No accuracy claims without labeled multilingual evidence.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Normalization result
# ---------------------------------------------------------------------------

@dataclass
class NormalizationResult:
    original: str
    normalized: str
    detected_language: str          # english | hindi_transliterated | hinglish | mixed | unknown
    transformations_applied: List[str] = field(default_factory=list)
    confidence: float = 0.0         # 0.0-1.0: confidence in language detection


# ---------------------------------------------------------------------------
# OCR artifact corrections (character substitutions caused by poor OCR)
# ---------------------------------------------------------------------------

_OCR_CORRECTIONS = [
    # Digit-for-letter substitutions
    (re.compile(r'\b0TP\b', re.IGNORECASE), 'OTP'),
    (re.compile(r'\bOTP\b', re.IGNORECASE), 'OTP'),      # ensure uppercase
    (re.compile(r'\b0tp\b', re.IGNORECASE), 'OTP'),
    (re.compile(r'p[@a]ssw[o0]rd', re.IGNORECASE), 'password'),
    (re.compile(r'acc[o0]unt', re.IGNORECASE), 'account'),
    (re.compile(r'l[o0]gin', re.IGNORECASE), 'login'),
    (re.compile(r'verif[i1]cati[o0]n', re.IGNORECASE), 'verification'),
    (re.compile(r'c[o0]nfirm', re.IGNORECASE), 'confirm'),
    # Spacing artifacts in OCR (merged words)
    (re.compile(r'onetime', re.IGNORECASE), 'one time'),
    (re.compile(r'onepass', re.IGNORECASE), 'one pass'),
    # Punctuation splitting (O-T-P)
    (re.compile(r'\bO[\.\-]T[\.\-]P\b', re.IGNORECASE), 'OTP'),
    (re.compile(r'\bO T P\b', re.IGNORECASE), 'OTP'),
]

# ---------------------------------------------------------------------------
# ASR transcription variation corrections
# ---------------------------------------------------------------------------

_ASR_CORRECTIONS = [
    # Common ASR mishearings of security-relevant terms
    (re.compile(r'\botpee\b', re.IGNORECASE), 'OTP'),
    (re.compile(r'\boh tee pee\b', re.IGNORECASE), 'OTP'),
    (re.compile(r'\bpaasword\b', re.IGNORECASE), 'password'),
    (re.compile(r'\bpassword\b', re.IGNORECASE), 'password'),
    (re.compile(r'\bpin number\b', re.IGNORECASE), 'PIN'),
    (re.compile(r'\bpin no\b', re.IGNORECASE), 'PIN'),
    (re.compile(r'\bsend me your\b', re.IGNORECASE), 'send me your'),
    (re.compile(r'\bshare karna\b', re.IGNORECASE), 'share karna'),    # ASR of Hindi
    (re.compile(r'\babhi bhejo\b', re.IGNORECASE), 'abhi bhejo'),
]

# ---------------------------------------------------------------------------
# Hindi transliteration patterns (Latin-script Hindi used in WhatsApp)
# These are DETECTION patterns — we map them to English equivalents
# for downstream safety detectors, while preserving the original.
# ---------------------------------------------------------------------------

# Credential-related Hindi/Hinglish
_HINDI_CREDENTIAL_PATTERNS = [
    # OTP request patterns
    (re.compile(
        r'(otp|code|verification code)\s*(share\s*karo|bhejo|do\s*na|bata\s*do|dijiye|de\s*do)',
        re.IGNORECASE
    ), 'share otp request'),
    (re.compile(
        r'(apna|aapka)\s*(otp|code|pin|password)\s*(share|send|bhejo|do)',
        re.IGNORECASE
    ), 'share credential request'),
    # Account blocking in Hindi
    (re.compile(
        r'(khata|account|id)\s*(band|block|deactivate)\s*(ho\s*jayega|kar\s*diya\s*jayega)',
        re.IGNORECASE
    ), 'account blocking threat'),
    (re.compile(
        r'account\s*(block|band)\s*ho\s*(gaya|jayega|sakta)',
        re.IGNORECASE
    ), 'account blocking threat'),
    # Urgent payment pressure
    (re.compile(
        r'(abhi|turant|jaldi)\s*(pay|bhejo|transfer|de\s*do)',
        re.IGNORECASE
    ), 'urgent payment pressure'),
    (re.compile(
        r'(turant|abhi|jaldi|urgent)\s*(action|karo|kijiye)',
        re.IGNORECASE
    ), 'urgent action pressure'),
    # Reward / lottery
    (re.compile(
        r'(inaam|prize|reward|lottery)\s*(jeet[a-z]*|mila|aapko)',
        re.IGNORECASE
    ), 'reward or lottery claim'),
    (re.compile(
        r'aapne\s*(jeet[a-z]*|lucky)\s*(draw|prize|inaam)',
        re.IGNORECASE
    ), 'reward or lottery claim'),
    # Credential warning (NOT a risk — opposite signal)
    (re.compile(
        r'(kisi\s*(ko|se)|kabhi)\s*(otp|password|pin)\s*(share|bhejo|do|mat\s*karo)',
        re.IGNORECASE
    ), 'credential warning'),
    (re.compile(
        r'(otp|password|pin)\s*(share\s*mat|share\s*na|kabhi\s*mat)',
        re.IGNORECASE
    ), 'credential warning'),
]

# Hinglish urgency patterns
_HINGLISH_URGENCY_PATTERNS = [
    (re.compile(r'\bturant\b', re.IGNORECASE), 'immediately'),
    (re.compile(r'\bjaldi\b', re.IGNORECASE), 'quickly'),
    (re.compile(r'\babhi\b', re.IGNORECASE), 'right now'),
    (re.compile(r'\bfauran\b', re.IGNORECASE), 'immediately'),
    (re.compile(r'\burgent hai\b', re.IGNORECASE), 'is urgent'),
    (re.compile(r'\bder mat karo\b', re.IGNORECASE), 'do not delay'),
    (re.compile(r'\btime pe\b|\btime par\b', re.IGNORECASE), 'on time'),
]

# ---------------------------------------------------------------------------
# Language detection heuristics
# ---------------------------------------------------------------------------

_HINDI_INDICATOR_WORDS = frozenset([
    'aap', 'apna', 'abhi', 'turant', 'jaldi', 'bhejo', 'karo', 'kijiye',
    'dijiye', 'chahiye', 'rahega', 'jayega', 'gaya', 'milega', 'hoga',
    'khata', 'khata', 'inaam', 'nahin', 'nahi', 'bata', 'paise', 'paisa',
    'rupaye', 'khata', 'band', 'jeet', 'lucky', 'draw', 'sabse', 'zyada',
    'bahut', 'thoda', 'ek', 'do', 'teen', 'char', 'paanch', 'das', 'sau',
    'hazaar', 'lakh', 'crore', 'kya', 'kyun', 'kaun', 'kab', 'kaise',
    'fauran', 'der', 'mat', 'kabhi', 'bhi', 'sirf', 'yahan', 'wahan',
])

_ENGLISH_ONLY_WORDS = frozenset([
    'the', 'and', 'for', 'that', 'this', 'with', 'have', 'from', 'your',
    'been', 'will', 'they', 'what', 'when', 'were', 'their', 'there',
    'hello', 'please', 'order', 'shipped', 'today', 'message', 'delivery',
    'account', 'payment', 'click', 'link', 'verify', 'update', 'dear',
])


def _detect_language(text: str) -> Tuple[str, float]:
    """
    Heuristically detect language family.
    Returns (language, confidence).
    Does not claim high accuracy — used for logging and uncertainty tracking.
    """
    tokens = set(re.findall(r'\b[a-z]{2,}\b', text.lower()))
    hindi_hits = len(tokens & _HINDI_INDICATOR_WORDS)
    english_hits = len(tokens & _ENGLISH_ONLY_WORDS)
    total = max(1, len(tokens))

    if hindi_hits > 2 and english_hits < 3:
        lang = 'hindi_transliterated'
        conf = min(0.75, hindi_hits / total * 3)
    elif hindi_hits > 0 and english_hits > 0:
        lang = 'hinglish'
        conf = min(0.70, (hindi_hits + english_hits) / total * 2)
    elif english_hits > 2:
        lang = 'english'
        conf = min(0.90, english_hits / total * 3)
    else:
        lang = 'unknown'
        conf = 0.3

    return lang, round(conf, 2)


# ---------------------------------------------------------------------------
# Main normalization function
# ---------------------------------------------------------------------------

def normalize_for_safety(text: str, apply_ocr: bool = True, apply_asr: bool = False) -> NormalizationResult:
    """
    Normalize text for defensive safety detection.

    Args:
        text: original message text (or extracted OCR / ASR transcript)
        apply_ocr: True when text comes from image OCR (apply OCR corrections)
        apply_asr: True when text comes from voice ASR (apply ASR corrections)

    Returns:
        NormalizationResult with original preserved, normalized form, language, transformations.
    """
    if not text or not text.strip():
        return NormalizationResult(
            original=text or '',
            normalized='',
            detected_language='unknown',
            confidence=0.0
        )

    original = text
    normalized = unicodedata.normalize('NFKC', text)
    transformations = []

    # 1. OCR corrections (for image-derived text)
    if apply_ocr:
        for pattern, replacement in _OCR_CORRECTIONS:
            new_text = pattern.sub(replacement, normalized)
            if new_text != normalized:
                transformations.append(f'ocr_correction:{replacement.lower()}')
                normalized = new_text

    # 2. ASR corrections (for voice-derived text)
    if apply_asr:
        for pattern, replacement in _ASR_CORRECTIONS:
            new_text = pattern.sub(replacement, normalized)
            if new_text != normalized:
                transformations.append(f'asr_correction:{replacement.lower()}')
                normalized = new_text

    # 3. Whitespace normalization
    normalized_ws = re.sub(r'\s+', ' ', normalized).strip()
    if normalized_ws != normalized:
        transformations.append('whitespace_collapsed')
    normalized = normalized_ws

    # 4. Language detection
    lang, conf = _detect_language(normalized)

    return NormalizationResult(
        original=original,
        normalized=normalized,
        detected_language=lang,
        transformations_applied=transformations,
        confidence=conf,
    )


# ---------------------------------------------------------------------------
# Hindi/Hinglish safety signal extraction
# ---------------------------------------------------------------------------

def extract_multilingual_signals(normalized_text: str) -> dict:
    """
    Extract safety-relevant signals from normalized text,
    including Hindi transliteration and Hinglish patterns.

    Returns a dict of signal_name -> bool, for consumption by safety_detectors.py.
    All returned booleans are conservative — false negatives preferred over false positives
    for legitimate messages.
    """
    signals = {
        'ml_credential_request': False,
        'ml_credential_warning': False,
        'ml_account_blocking': False,
        'ml_urgent_payment': False,
        'ml_urgent_action': False,
        'ml_reward_lottery': False,
        'ml_urgency_language': False,
    }

    text = normalized_text.lower()

    for pattern, signal_label in _HINDI_CREDENTIAL_PATTERNS:
        if pattern.search(text):
            if signal_label == 'credential warning':
                signals['ml_credential_warning'] = True
            elif signal_label in ('share otp request', 'share credential request'):
                signals['ml_credential_request'] = True
            elif signal_label == 'account blocking threat':
                signals['ml_account_blocking'] = True
            elif signal_label == 'urgent payment pressure':
                signals['ml_urgent_payment'] = True
            elif signal_label == 'urgent action pressure':
                signals['ml_urgent_action'] = True
            elif signal_label == 'reward or lottery claim':
                signals['ml_reward_lottery'] = True

    for pattern, _ in _HINGLISH_URGENCY_PATTERNS:
        if pattern.search(text):
            signals['ml_urgency_language'] = True
            break

    return signals
