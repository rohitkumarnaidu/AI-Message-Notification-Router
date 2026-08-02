# Phase 18: Test & Evaluation Handoff Specification

## 1. Executive Summary
This document specifies the complete test and evaluation harness for the **HackerRank Orchestrate Message Notification Router**. 

The verification suite consists of **118 unit, integration, safety policy, and quality tests**. The entire suite executes offline in **~1.09 seconds**, requiring **zero external network access or live provider API keys**.

---

## 2. Execution Command & Verified Test Results

### Primary Test Execution Command
```bash
python -m pytest tests/ -q
```

### Verified Benchmark Execution Output
```text
C:\Users\Dell\AppData\Roaming\Python\Python314\site-packages\pytest_asyncio\plugin.py:208: PytestDeprecationWarning: ...
........................................................................ [ 61%]
..............................................                           [100%]

============================== 118 passed in 1.09s ==============================
```

- **Total Test Suites**: 10 Core Test Modules
- **Total Executed Tests**: 118
- **Passed**: 118 (100% Pass Rate)
- **Failed**: 0
- **Execution Time**: ~1.09s
- **Provider API Keys Required**: **NO** (100% Offline Mocks & Deterministic Rules)

---

## 3. Comprehensive Test Suite Inventory

| Test Module File | Test Focus & Verification Domain | Test Count | Provider Required |
|---|---|---|---|
| `tests/test_baseline.py` | Baseline routing heuristics, scam overrides, OTP protections, greetings, and default fallback. | ~20 | No |
| `tests/test_safety_detectors.py` | Safety signal extraction, credential requests vs warnings, payment pressure, pressure patterns, and link trust analysis. | ~15 | No |
| `tests/test_multilingual_safety.py` | Multilingual safety normalization (Hinglish, transliterated text, Hindi keywords, OCR/ASR safety signals). | ~12 | No |
| `tests/test_payment_credential_policy.py` | Payment risk detection, credential phishing policies, verified business exceptions, and OTP scam block rules. | ~15 | No |
| `tests/test_injection_regressions.py` | Prompt injection detection, system prompt override attempts, instruction boundary defense, and payload isolation. | ~12 | No |
| `tests/test_unsafe_notify_validator.py` | Safety gate preventing unsafe `notify` actions on risky content, unverified media, or credential requests. | ~10 | No |
| `tests/test_urgency_manipulation.py` | Distinguishing concrete time deadlines from vague urgency language or coercive artificial pressure. | ~10 | No |
| `tests/test_phase13_lanes.py` | Phase 13 temporal context extraction, quiet hours downgrade, notification load governance, and group policy. | ~8 | No |
| `tests/test_phase14_router.py` | Phase 14 preclassifier decision boundaries, selective hybrid escalation, and execution mode tracking. | ~8 | No |
| `tests/test_phase15_quality.py` | Phase 15 quality checks: evidence ID consistency, reason builder format, confidence calibration, and output schema validation. | ~8 | No |
| **Total Suite** | **Comprehensive Regression & Safety Governance Verification** | **118** | **No** |

---

## 4. Test Harness Design Principles

1. **Zero External Dependency**: All tests use mocked contexts, deterministic signal structures, or standard test fixtures (`tests/fixtures/`).
2. **Fast Feedback Loop**: Full execution completes in under 2 seconds, making it suitable for continuous integration (CI) environments.
3. **Safety First Policy Coverage**: Tests explicitly verify that high-risk conditions (credential requests, prompt injections, impersonation scams) NEVER receive a `notify` action under any circumstances.
4. **Contract Rigor**: Validates that output fields, enum values, confidence bounds `[0.30, 0.99]`, and evidence ID formats strictly adhere to `output_contract.md`.
