# AI Judge Metrics Sheet

## Official Solved Sample Metrics
- Dataset: dataset/messages.csv (30 solved sample rows)
- Action Accuracy: 1.0000 (30/30)
- Action Macro F1: 1.0000
- Notify Recall: 1.0000
- Digest Recall: 1.0000
- Mute Recall: 1.0000
- Type Accuracy: 1.0000 (30/30)
- Type Macro F1: 1.0000
- Evaluator Command: python code/evaluate.py --mode solved-audit
- Source Commit: ea2c3ac
- Limitation: Evaluated on official 30-message solved subset.

## Internal Adversarial & Regression Test Metrics
- Suite: pytest tests/
- Passed Tests: 118 / 118 (100% pass rate)
- Duration: 1.62 seconds
- Provider Dependency: None (Deterministic offline tests)

## Full Dataset Prediction Distribution (110 Rows)
- Dataset: dataset/messages.csv (110 total incoming messages)
- Output File: output.csv (11,737 bytes, SHA-256: c19998711dae2962e5c64fcbf821d7b6d73510d2ac28f0c655854cb516491d06)
- Action Distribution: digest: 52 (47.3%), mute: 47 (42.7%), notify: 11 (10.0%)
- Message Type Distribution: unknown: 44, scam: 22, urgent: 13, forward: 12, spam: 8, promotion: 6, personal: 2, event: 1, greeting: 1, payment: 1
- Evidence Attachment: none: 58 (52.7%), 1 ID: 26 (23.6%), 2 IDs: 18 (16.4%), 3 IDs: 8 (7.3%)
- Confidence Calibration: min=0.85, max=0.99, avg=0.87, exact 1.0=0 rows
