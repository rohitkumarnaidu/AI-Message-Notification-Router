---
layout: default
title: Policy Engine
parent: Architecture
nav_order: 2
---

# 27-Rule Policy Engine
{: .no_toc }

A deterministic, tiered policy engine that maps extracted features to routing decisions. Safety-first design ensures scams are caught before urgency is evaluated.
{: .fs-6 .fw-300 }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Design Philosophy

The policy engine evaluates rules in **strict priority order**. Once a rule matches, no further rules are checked. This guarantees:

- **Safety rules always fire first** — a scam message can never reach the "notify" tier
- **Deterministic behavior** — same input always produces same output
- **Full auditability** — every decision traces back to a specific rule number

---

## Rule Tiers

### Tier 1: Safety Gate (Rules 1-8) → `mute/scam`

| Rule | Condition | Confidence |
|:-----|:----------|:-----------|
| 1 | Prompt injection detected | 0.92 |
| 2 | OTP request + (account block threat OR suspicious link OR untrusted sender) | 0.90 |
| 3 | Credential request + untrusted sender | 0.88 |
| 4 | Account block threat + (suspicious link OR unverified business) | 0.87 |
| 5 | Payment pressure + QR code + unverified business | 0.86 |
| 6 | Lottery/prize claim + unverified business | 0.85 |
| 7 | Domain mismatch + high business reports | 0.84 |
| 8 | Financial data request + untrusted sender | 0.88 |

### Tier 2: Forward Spam (Rules 9-10) → `mute/forward`

| Rule | Condition | Confidence |
|:-----|:----------|:-----------|
| 9 | High forward count + historical mute signal | 0.82 |
| 10 | High forward count + historical dismiss + no historical reply | 0.78 |

### Tier 3: Opt-Out (Rules 11-12) → `mute/promotion`

| Rule | Condition | Confidence |
|:-----|:----------|:-----------|
| 11 | User opted out + promotion language | 0.82 |
| 12 | Historical mute + no urgency + not admin | 0.78 |

### Tier 4: Notify Conditions (Rules 13-18) → `notify/*`

| Rule | Condition | Type | Confidence |
|:-----|:----------|:-----|:-----------|
| 13 | Immediate time ref + group admin + no safety flags | `urgent` | 0.88 |
| 14 | Deadline + trusted sender/admin + no suspicious link | `urgent/event` | 0.86 |
| 15 | Verified business + active transaction + no safety flags | `business_update` | 0.88 |
| 16 | Direct mention + trusted + immediate time ref | `urgent` | 0.85 |
| 17 | Trusted personal + immediate time ref + no suspicious link | `urgent` | 0.84 |
| 18 | Waiting signal + trusted/admin/verified | `urgent/business` | 0.85 |

### Tier 5: History Mute (Rule 19) → `mute/spam`

| Rule | Condition | Confidence |
|:-----|:----------|:-----------|
| 19 | Historical report + historical dismiss | 0.80 |

### Tier 6: Digest (Rules 20-26) → `digest/*`

| Rule | Condition | Type | Confidence |
|:-----|:----------|:-----|:-----------|
| 20 | Verified business + opted in + promotion language | `promotion` | 0.76 |
| 21 | Explicit opt-in + promotion language | `promotion` | 0.78 |
| 22 | Event date + no urgency + no suspicious link | `event` | 0.78 |
| 23 | Verified business + not opted out + not promo | `business_update` | 0.76 |
| 24 | Greeting + no suspicious link | `greeting` | 0.76 |
| 25 | Historical dismiss + no urgency + not admin | `personal/promo` | 0.74 |
| 26 | Known sender + no safety flags | `personal` | 0.74 |

### Tier 7: Default (Rule 27) → `digest/unknown`

| Rule | Condition | Confidence |
|:-----|:----------|:-----------|
| 27 | No other rule matched | 0.60 |

{: .note }
The default action is `digest` (not `mute`) to prevent information loss. Unknown messages are batched into the daily summary rather than silenced.

---

## Confidence Adjustments

After the base confidence is set by the rule, adjustments are applied:

| Factor | Effect |
|:-------|:-------|
| Historical reply signal | **+0.04** |
| Historical dismiss signal (for mute/digest) | **+0.03** |
| Historical report signal (for mute) | **+0.04** |
| Verified business (for business types) | **+0.02** |
| Active transaction (for notify) | **+0.03** |
| Domain mismatch (for scam) | **+0.03** |
| Missing context | **−0.06** |
| Media present but unavailable | **−0.04** |
| High forward count in non-spam rule | **−0.02** |
| Low specificity rule (24+) | **−0.04** |

Final confidence is clamped to `[0.0, 1.0]`.
