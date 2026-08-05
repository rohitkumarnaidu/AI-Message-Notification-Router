---
layout: default
title: Safety Engine
parent: Architecture
nav_order: 1
---

# Safety Detection Engine
{: .no_toc }

The heart of the system's intelligence — a multi-layer deterministic defense system that operates without any LLM involvement.
{: .fs-6 .fw-300 }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Trust Hierarchy

The system operates on a **zero-trust principle**. Every input is classified by trust level:

| Level | Source | Trust |
|:------|:-------|:------|
| 1 | Official Policy Rules (`baseline_policy.py`) | 🔒 Absolute — cannot be overridden |
| 2 | Deterministic Schema Contracts (`validators.py`) | 🔒 Enforced — invalid outputs rejected |
| 3 | Trusted Metadata (user preferences, admin status) | 🔐 High — verified by platform |
| 4 | Validated History (past events with user_id isolation) | 🔐 Medium — cross-user rejected |
| 5 | Model Proposal (LLM or preclassifier output) | ⚠️ Low — subordinate to policy |
| 6 | Retrieved Evidence Text | ⚠️ Low — treated as untrusted |
| 7 | Current Message Content (text, OCR, transcript) | 🚨 Untrusted — primary attack surface |

---

## 7 Safety Detectors

### Credential Risk Detector

Distinguishes **requests** from **warnings**:

| Input | Classification |
|:------|:---------------|
| `"Send me your OTP now"` | ⛔ CREDENTIAL_REQUEST → mute/scam |
| `"Never share your OTP with anyone"` | ✅ CREDENTIAL_WARNING → safe |

{: .warning }
Trusted sender status reduces confidence but **never suppresses** the credential risk flag.

### Payment Risk Detector

Distinguishes **suspicious** from **legitimate** payment messages:

| Signal | Classification |
|:-------|:---------------|
| Unknown destination + pressure + no order ID | ⛔ Suspicious → mute |
| Verified business + order ID + EMI due | ✅ Legitimate → digest/notify |

### Pressure Signal Detector

Detects three categories of social engineering:

- **Account blocking:** `"Your account will be blocked in 24 hours"`
- **Reward/lottery:** `"Congratulations! You won a prize"`
- **Impersonation:** `"This is RBI official"`

### Prompt Injection Detector

Detects **17 attack patterns** including:

- Action override: `"set action = notify"`
- Confidence manipulation: `"set confidence to 1.0"`
- System authority claims: `"ignore previous instructions"`
- Safety bypass: `"disable safety filters"`

{: .note }
Safe contexts like `"notify me when the package arrives"` are automatically excluded as false positives.

### Urgency Detector

Distinguishes **concrete deadlines** from **vague pressure**:

| Signal | Classification |
|:-------|:---------------|
| `"I am waiting outside"` | ✅ Concrete deadline → notify |
| `"This is urgent please respond"` | ⚠️ Vague urgency → digest |
| `"Meeting scheduled for next week"` | 📅 Future event → digest |

### Link/Domain Analyzer

Classifies URLs without making network requests:

| Domain | Trust |
|:-------|:------|
| `amazon.in`, `flipkart.com`, `google.com` | ✅ Trusted |
| `bit.ly`, `tinyurl.com` | ⚠️ URL Shortener → suspicious |
| `secure-verify.com/account-login` | ⛔ Suspicious path |

### Evidence Safety Validator

Rejects invalid evidence IDs:

- ❌ Incoming message ID used as evidence
- ❌ Event IDs used as evidence
- ❌ Future timestamps
- ❌ Cross-user evidence
- ❌ Duplicate evidence IDs

---

## 11 Risk Categories

| Tier | Category | Action Constraint |
|:-----|:---------|:------------------|
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

## Security Guarantees

| Guarantee | How It's Enforced |
|:----------|:------------------|
| Scam messages can NEVER be `notify` | `unsafe_notify_validator.py` blocks all scam+notify |
| Credential requests can NEVER be safe | Trusted sender only reduces confidence, never suppresses risk |
| Prompt injection can NEVER override routing | Injection is flagged but cannot change `action` or `confidence` |
| Evidence is user-isolated | Cross-user, future, duplicate evidence rejected |
| API keys never enter the pipeline | Environment variables only |
| Failed media ≠ safe media | OCR/ASR failure sets `media_grounding_quality=failed` |

---

## Multilingual Safety

| Capability | Example |
|:-----------|:--------|
| OCR Artifact Correction | `0TP` → `OTP`, `p@ssword` → `password` |
| ASR Variation Handling | `otpee` → `OTP` |
| Hindi Credential Request | `apna OTP share karo abhi` → detected |
| Hindi Account Blocking | `aapka account band ho jayega` → detected |
| Hindi Urgency | `turant karo yeh kaam` → detected |
| NFKC Normalization | Applied before all pattern matching |
