---
layout: default
title: Safety Architecture
---

# 🛡️ Safety Architecture

The AI Message Notification Router operates on a **zero-trust principle** — no single input source is ever trusted unconditionally.

---

## Trust Hierarchy

Every input is classified by trust level (highest to lowest):

| Level | Source | Trust |
|-------|--------|-------|
| 1 | Official Policy Rules (hardcoded in `baseline_policy.py`) | 🔒 Absolute — cannot be overridden |
| 2 | Deterministic Schema Contracts (`validators.py`) | 🔒 Enforced — invalid outputs rejected |
| 3 | Trusted Metadata (user preferences, admin status) | 🔐 High — verified by platform |
| 4 | Validated History (past events with user_id isolation) | 🔐 Medium — cross-user rejected |
| 5 | Model Proposal (LLM or preclassifier output) | ⚠️ Low — subordinate to policy |
| 6 | Retrieved Evidence Text | ⚠️ Low — treated as untrusted |
| 7 | Current Message Content (text, OCR, transcript) | 🚨 Untrusted — primary attack surface |

---

## 7 Safety Detectors

| Detector | What It Detects | Module |
|----------|----------------|--------|
| **Credential Risk** | OTP/password/PIN requests vs warnings | `safety_detectors.py` |
| **Payment Risk** | Suspicious vs legitimate payment pressure | `safety_detectors.py` |
| **Pressure Signals** | Account blocking, lottery, impersonation | `safety_detectors.py` |
| **Prompt Injection** | 17 attack patterns with false-positive suppression | `safety_detectors.py` |
| **Urgency Analysis** | Concrete deadlines vs vague pressure | `safety_detectors.py` |
| **Link/Domain** | Trusted vs shortener vs suspicious URLs | `safety_detectors.py` |
| **Evidence Safety** | Cross-user, future, duplicate, self-referential rejection | `safety_detectors.py` |

---

## 11 Risk Categories

| Tier | Category | Action Constraint |
|------|----------|-------------------|
| 0 | `NONE` | No constraint |
| 1 | `LOW_VALUE` | Digest or Mute |
| 2 | `SPAM` / `PROMOTION_UNWANTED` | Mute |
| 3 | `DANGEROUS_FORWARD` | Mute |
| 4 | `PROMPT_INJECTION` / `UNKNOWN_HIGH_RISK` | Mute |
| 5 | `IMPERSONATION_RISK` | Mute |
| 6 | `PAYMENT_RISK` | Mute |
| 7 | `PHISHING_RISK` | Mute |
| 8 | `CREDENTIAL_RISK` | Always Mute |

---

## Key Security Guarantees

- ✅ **Scam messages can NEVER be `notify`** — `unsafe_notify_validator.py` blocks all scam+notify
- ✅ **Credential requests can NEVER be safe** — Trusted sender only reduces confidence, never suppresses risk
- ✅ **Prompt injection can NEVER override routing** — Injection is flagged but cannot change `action` or `confidence`
- ✅ **Evidence is user-isolated** — Cross-user, future, duplicate, and self-referential evidence rejected
- ✅ **API keys never enter the pipeline** — Environment variables only, never committed
- ✅ **Failed media ≠ safe media** — OCR/ASR failure sets `media_grounding_quality=failed`, never assumed safe

---

## Multilingual Safety

The system normalizes text across English, Hindi (transliterated), and Hinglish before running safety detectors:

| Capability | Example |
|------------|---------|
| OCR Artifact Correction | `0TP` → `OTP`, `p@ssword` → `password` |
| ASR Variation Handling | `otpee` → `OTP` |
| Hindi Credential Request | `apna OTP share karo abhi` → detected |
| Hindi Account Blocking | `aapka account band ho jayega` → detected |
| NFKC Unicode Normalization | Applied before all pattern matching |

---

[← Back to Home](index)
