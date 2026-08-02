# Phase 15 Confidence Calibration Audit

- Calibrated via `code/confidence.py`.
- Clamped to `[0.30, 0.99]`.
- Automatic `1.00` assigned count: 0 (prevented by strict clamp).
- Penalties applied for fallbacks, schema repairs, and signal conflicts.
