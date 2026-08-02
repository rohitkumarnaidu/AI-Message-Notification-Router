# Confidence Strategy

Confidence is NOT simply the raw probability score from the LLM. It is calibrated deterministically.

## Inputs
- LLM self-reported confidence.
- Deterministic signal agreement (does the regex engine agree with the LLM?).
- Context completeness (`missing_context` flags).
- Media extraction success.

## Adjustments
- **+0.10**: Strong historical evidence supports the decision (e.g., previous reply to this exact sender).
- **-0.10**: Media extraction failed, forcing text-only fallback.
- **-0.15**: Missing relationship context (e.g., group message but user not in `group_members.csv`).
- **1.00 (Fixed)**: Applied automatically if a Deterministic Safety Override (e.g., Scam block) is triggered.

## Calibration Plan
Confidence will be clamped between `0.0` and `1.0`. Final tuning will be performed on the 30-sample dataset during Phase 5 implementation.
