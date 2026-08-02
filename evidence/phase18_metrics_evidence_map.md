# Phase 18 Metrics & Grounded Evidence Map

## Executive Overview
This document maps **every system performance metric** to its exact empirical source. It specifies the dataset, evaluation mode, sample count, prediction file path, expected label file path, evaluator execution command, git source commit, report output path, and operational limitations for every claim.

---

## Metric Mapping Matrix

| Metric Name | Value | Dataset / Mode | Sample Count | Prediction File Path | Expected File Path | Evaluator Command | Source Commit | Report Output Path | Scope & Limitation |
|---|---|---|---|---|---|---|---|---|---|
| **Action Accuracy** | **1.0000 (100.0%)** | `solved` mode | 30 solved samples | `outputs/phase15_release_candidate.csv` | `dataset/sample_messages.csv` | `python code/evaluate.py --mode solved --input outputs/phase15_release_candidate.csv --expected dataset/sample_messages.csv --output outputs/phase15_release_candidate.csv --report evaluation/phase15_solved_report.json` | `ea2c3ac` | [`evaluation/phase15_solved_report.json`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/evaluation/phase15_solved_report.json) | Evaluated on the 30-message solved subset in `sample_messages.csv`. |
| **Action Macro F1** | **1.0000** | `solved` mode | 30 solved samples | `outputs/phase15_release_candidate.csv` | `dataset/sample_messages.csv` | `python code/evaluate.py --mode solved --input outputs/phase15_release_candidate.csv --expected dataset/sample_messages.csv --output outputs/phase15_release_candidate.csv --report evaluation/phase15_solved_report.json` | `ea2c3ac` | [`evaluation/phase15_solved_report.json`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/evaluation/phase15_solved_report.json) | Unweighted harmonic mean of F1 across notify, digest, mute. |
| **Notify Recall** | **1.0000 (100.0%)** | `solved` mode | 8 notify samples | `outputs/phase15_release_candidate.csv` | `dataset/sample_messages.csv` | `python code/evaluate.py --mode solved --input outputs/phase15_release_candidate.csv --expected dataset/sample_messages.csv --output outputs/phase15_release_candidate.csv --report evaluation/phase15_solved_report.json` | `ea2c3ac` | [`evaluation/phase15_solved_report.json`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/evaluation/phase15_solved_report.json) | Perfect recall on high-priority time-sensitive operational updates. |
| **Digest Recall** | **1.0000 (100.0%)** | `solved` mode | 11 digest samples | `outputs/phase15_release_candidate.csv` | `dataset/sample_messages.csv` | `python code/evaluate.py --mode solved --input outputs/phase15_release_candidate.csv --expected dataset/sample_messages.csv --output outputs/phase15_release_candidate.csv --report evaluation/phase15_solved_report.json` | `ea2c3ac` | [`evaluation/phase15_solved_report.json`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/evaluation/phase15_solved_report.json) | Correctly routes non-urgent informational updates to digest. |
| **Mute Recall** | **1.0000 (100.0%)** | `solved` mode | 11 mute samples | `outputs/phase15_release_candidate.csv` | `dataset/sample_messages.csv` | `python code/evaluate.py --mode solved --input outputs/phase15_release_candidate.csv --expected dataset/sample_messages.csv --output outputs/phase15_release_candidate.csv --report evaluation/phase15_solved_report.json` | `ea2c3ac` | [`evaluation/phase15_solved_report.json`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/evaluation/phase15_solved_report.json) | 100% detection of scams, spam, and unwanted marketing. |
| **Message Type Accuracy** | **1.0000 (100.0%)** | `solved` mode | 30 solved samples | `outputs/phase15_release_candidate.csv` | `dataset/sample_messages.csv` | `python code/evaluate.py --mode solved --input outputs/phase15_release_candidate.csv --expected dataset/sample_messages.csv --output outputs/phase15_release_candidate.csv --report evaluation/phase15_solved_report.json` | `ea2c3ac` | [`evaluation/phase15_solved_report.json`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/evaluation/phase15_solved_report.json) | Correctly classifies 11 canonical message taxonomy types. |
| **Message Type Macro F1** | **1.0000** | `solved` mode | 30 solved samples | `outputs/phase15_release_candidate.csv` | `dataset/sample_messages.csv` | `python code/evaluate.py --mode solved --input outputs/phase15_release_candidate.csv --expected dataset/sample_messages.csv --output outputs/phase15_release_candidate.csv --report evaluation/phase15_solved_report.json` | `ea2c3ac` | [`evaluation/phase15_solved_report.json`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/evaluation/phase15_solved_report.json) | Macro F1 across all supported message categories. |
| **Safety Test Pass Rate** | **118 / 118 (100.0%)** | `pytest` suite | 118 unit tests | `tests/` | N/A | `python -m pytest tests/` | `ea2c3ac` | [`evidence/phase15_policy_regression.md`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/evidence/phase15_policy_regression.md) | Unit tests cover credential theft, payment risk, prompt injection, quiet hours, load. |
| **Unsafe-Notify Leaks** | **0 Remaining** | `unlabeled-audit` | 110 messages | `outputs/phase15_release_candidate.csv` | `dataset/messages.csv` | `python code/evaluate.py --mode unlabeled-audit --input dataset/messages.csv --output outputs/phase15_release_candidate.csv --report evaluation/phase15_report.json` | `ea2c3ac` | [`evidence/phase12_unsafe_notify.md`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/evidence/phase12_unsafe_notify.md) | Verified by `unsafe_notify_validator.py` on full 110 dataset. |
| **Evidence Validity Rate** | **100.0%** | `unlabeled-audit` | 110 messages | `outputs/phase15_release_candidate.csv` | `dataset/messages.csv` | `python code/evaluate.py --mode unlabeled-audit --input dataset/messages.csv --output outputs/phase15_release_candidate.csv --report evaluation/phase15_report.json` | `ea2c3ac` | [`evidence/phase15_evidence_audit.md`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/evidence/phase15_evidence_audit.md) | Zero future timestamp leakage, zero cross-user leaks, zero hallucinated IDs. |
| **Preclassified Fast-Path Rate** | **55.4% (61/110)** | `unlabeled-audit` | 110 messages | `outputs/phase15_release_candidate.csv` | `dataset/messages.csv` | `python code/evaluate.py --mode unlabeled-audit --input dataset/messages.csv --output outputs/phase15_release_candidate.csv --report evaluation/phase15_report.json` | `ea2c3ac` | [`evidence/phase14_decision_boundary.md`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/evidence/phase14_decision_boundary.md) | Fast-path deterministic preclassification executes in <1ms with 0 API calls. |
| **Schema Valid Rate** | **100.0% (1.0000)** | `structural` mode | 110 messages | `outputs/phase15_release_candidate.csv` | `dataset/messages.csv` | `python code/evaluate.py --mode structural --input dataset/messages.csv --output outputs/phase15_release_candidate.csv --report evaluation/phase15_report.json` | `ea2c3ac` | [`evidence/phase15_evaluator_validator.md`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/evidence/phase15_evaluator_validator.md) | 100% compliance with column names, data types, and allowed values. |
| **Regression Count** | **0 Regressions** | Release Audit | 110 messages | `outputs/phase15_release_candidate.csv` | `outputs/phase14_router_candidate.csv` | `python code/evaluate.py --mode unlabeled-audit --input dataset/messages.csv --output outputs/phase15_release_candidate.csv --report evaluation/phase15_report.json` | `ea2c3ac` | [`evidence/phase15_prior_candidate_comparison.md`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/evidence/phase15_prior_candidate_comparison.md) | Zero decision regressions between Phase 14 and Phase 15 candidate outputs. |
| **Artifact Hashes Valid** | **100.0% Verified** | Manifest Audit | 3 Deliverables | `code.zip`, `output.csv`, `log.txt` | `artifacts/phase16_submission_manifest.json` | `python build_phase16_submission.py --rehearse` | `ea2c3ac` | [`artifacts/phase16_submission_manifest.json`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/artifacts/phase16_submission_manifest.json) | `code.zip`: `0e94f545...`, `output.csv`: `c19998711...`, `log.txt`: `70fdc081...`. |

---

## Detailed Metric Verification Procedure

### 1. Solved Subset Metric Verification Command
```bash
python code/evaluate.py \
  --mode solved \
  --input outputs/phase15_release_candidate.csv \
  --expected dataset/sample_messages.csv \
  --output outputs/phase15_release_candidate.csv \
  --report evaluation/phase15_solved_report.json
```

### 2. Structural & Schema Audit Command
```bash
python code/evaluate.py \
  --mode structural \
  --input dataset/messages.csv \
  --output outputs/phase15_release_candidate.csv \
  --report evaluation/phase15_report.json
```

### 3. Safety Regression Test Suite Command
```bash
python -m pytest tests/
```

---

## Key Limitations & Scope Boundary
1. **Sample Size Scope**: Solved sample evaluation is calculated on the 30 solved records in `dataset/sample_messages.csv`.
2. **Hidden Test Set**: Final submission scoring occurs on HackerRank's hidden ground-truth dataset.
3. **Deterministic Fast-Path**: 55-60% of predictions are generated deterministically; remaining complex messages call the LLM chain.
