# Phase 14 Reason, Evidence, and Confidence Calibration

- **Grounded Reasons**: Concise, human-readable reasons explaining the action and message_type. No raw prompt text or API error leakages.
- **Evidence Calibration**: Evidence IDs strictly checked against `evidence_allowlist`. Uses `"none"` when no relevant evidence exists.
- **Confidence Calibration**: Clamped to `[0.00, 0.99]`. No automatic 1.00 assigned.
