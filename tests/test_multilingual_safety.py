"""
Phase 12 Safety Regression Tests — test_multilingual_safety.py

Tests multilingual normalization and Hinglish signal extraction.
No API calls, no network requests, no randomness.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))

from multilingual_safety import normalize_for_safety, extract_multilingual_signals


# ============================================================
# OCR CORRECTION TESTS
# ============================================================

def test_ocr_correction_0tp():
    """OCR digit-substitution '0TP' must be corrected to 'OTP' when apply_ocr=True."""
    result = normalize_for_safety('Share your 0TP now', apply_ocr=True)
    assert 'OTP' in result.normalized, (
        f"Expected 'OTP' in normalized output, got: '{result.normalized}'"
    )


def test_ocr_correction_punctuation_split():
    """OCR-split 'O-T-P' must be merged to 'OTP' when apply_ocr=True."""
    result = normalize_for_safety('Enter O-T-P here', apply_ocr=True)
    assert 'OTP' in result.normalized, (
        f"Expected 'OTP' in normalized output, got: '{result.normalized}'"
    )


def test_ocr_correction_password():
    """OCR variation 'p@ssword' must be corrected to 'password' when apply_ocr=True."""
    result = normalize_for_safety('Enter p@ssword to login', apply_ocr=True)
    assert 'password' in result.normalized.lower(), (
        f"Expected 'password' in normalized output, got: '{result.normalized}'"
    )


# ============================================================
# ASR CORRECTION TESTS
# ============================================================

def test_asr_correction_otpee():
    """ASR mishearing 'otpee' must be corrected to 'OTP' when apply_asr=True."""
    result = normalize_for_safety('Give me your otpee', apply_asr=True)
    assert 'OTP' in result.normalized, (
        f"Expected 'OTP' in normalized output after ASR correction, got: '{result.normalized}'"
    )


# ============================================================
# HINGLISH SIGNAL EXTRACTION TESTS
# ============================================================

def test_hinglish_otp_share():
    """Hinglish 'apna OTP share karo abhi' must set ml_credential_request=True."""
    signals = extract_multilingual_signals('apna OTP share karo abhi')
    assert signals.get('ml_credential_request') is True, (
        f"Expected ml_credential_request=True, got signals={signals}"
    )


def test_hinglish_account_block():
    """Hinglish account block threat must set ml_account_blocking=True."""
    signals = extract_multilingual_signals('aapka account band ho jayega')
    assert signals.get('ml_account_blocking') is True, (
        f"Expected ml_account_blocking=True, got signals={signals}"
    )


def test_hinglish_urgency():
    """Hinglish urgency word 'turant' must set ml_urgency_language=True."""
    signals = extract_multilingual_signals('turant karo yeh kaam')
    assert signals.get('ml_urgency_language') is True, (
        f"Expected ml_urgency_language=True for 'turant', got signals={signals}"
    )


def test_hinglish_lottery():
    """Hinglish lottery claim must set ml_reward_lottery=True."""
    signals = extract_multilingual_signals('aapne lucky draw jeeta hai')
    assert signals.get('ml_reward_lottery') is True, (
        f"Expected ml_reward_lottery=True for lottery claim, got signals={signals}"
    )


def test_hindi_credential_warning():
    """Hindi 'otp share mat karo kabhi' must set ml_credential_warning=True."""
    signals = extract_multilingual_signals('otp share mat karo kabhi')
    assert signals.get('ml_credential_warning') is True, (
        f"Expected ml_credential_warning=True for warning phrase, got signals={signals}"
    )


def test_english_no_false_positive():
    """Plain English shipment notification must not trigger any multilingual safety signals."""
    signals = extract_multilingual_signals('Your order has been shipped today')
    for key, val in signals.items():
        assert val is False, (
            f"Expected all signals=False for benign shipment notice, but {key}={val}"
        )


# ============================================================
# LANGUAGE DETECTION TESTS
# ============================================================

def test_language_detection_hindi():
    """Text with multiple Hindi indicator words must be detected as hindi/hinglish."""
    result = normalize_for_safety('abhi bhejo jaldi karo')
    assert result.detected_language in ('hindi_transliterated', 'hinglish'), (
        f"Expected hindi_transliterated or hinglish, got: '{result.detected_language}'"
    )


def test_language_detection_english():
    """Text with enough English-indicator words must be detected as 'english'."""
    # The language detector looks for tokens in _ENGLISH_ONLY_WORDS:
    # 'the', 'and', 'for', 'that', 'this', 'with', 'have', 'from', 'your', etc.
    # Need >2 hits to beat the english threshold. Use a sentence with several.
    result = normalize_for_safety('This is your confirmation for the order that was placed')
    assert result.detected_language == 'english', (
        f"Expected detected_language='english', got: '{result.detected_language}'"
    )


# ============================================================
# WHITESPACE NORMALIZATION TESTS
# ============================================================

def test_whitespace_collapse():
    """Multiple spaces and trailing whitespace must be collapsed to single spaces."""
    result = normalize_for_safety('hello   world  ')
    assert result.normalized == 'hello world', (
        f"Expected 'hello world' after whitespace collapse, got: '{result.normalized}'"
    )
