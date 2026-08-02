# Phase 3 — Baseline Specification

**Version**: baseline_v1
**Date**: 2026-08-02
**Status**: SPECIFICATION ONLY — not final architecture

---

## 1. Purpose

The baseline establishes:
- A valid end-to-end deterministic pipeline (input CSV → output CSV)
- A measurable starting point (accuracy on 30 solved samples)
- A catalog of failure categories
- Output-integrity protections
- Evidence for what complexity improvements would be justified

This is NOT the final production solution.

---

## 2. Inputs

| File | Purpose | Row Count |
| --- | --- | --- |
| `dataset/messages.csv` | Incoming messages to route | 110 |
| `dataset/users.csv` | User personalization signals | 54 |
| `dataset/groups.csv` | Group metadata | 23 |
| `dataset/group_members.csv` | Per-user-per-group signals | 401 |
| `dataset/business_accounts.csv` | Business trust and domain signals | 110 |
| `dataset/user_business_history.csv` | User-business opt-in/out and transaction history | 106 |
| `dataset/message_history.csv` | Historical messages for evidence | 412 |
| `dataset/message_events.csv` | Historical behavioral outcomes | 412 |
| `dataset/images.csv` | Image file paths | 20 |
| `dataset/voice_notes.csv` | Voice note file paths | 13 |
| `dataset/daily_notification_summary.csv` | Aggregate notification load | 756 |

---

## 3. Required Output Fields

| Column | Type | Valid Values |
| --- | --- | --- |
| message_id | string | must match input exactly |
| action | string | notify, digest, mute |
| message_type | string | personal, urgent, event, payment, business_update, promotion, greeting, forward, spam, scam, unknown |
| reason | string | non-empty, ≤200 chars |
| confidence | float | 0.0 to 1.0 inclusive, 2 decimal places |
| evidence_message_ids | string | 'none' or semicolon-separated message_0XXX IDs |

---

## 4. Rule Hierarchy

Rules are applied in priority order. The first matching rule determines `action` and `message_type`.

### Tier 1 — Safety (produces mute)
1. Prompt injection attempt → mute + scam (confidence ≥ 0.90)
2. OTP request + suspicious context → mute + scam
3. Credential request from untrusted sender → mute + scam
4. Account-block threat + suspicious link or unverified sender → mute + scam
5. QR payment pressure + unverified sender → mute + scam
6. Lottery/reward claim + unverified sender → mute + scam
7. Domain mismatch + high report count → mute + scam
8. Financial data request from untrusted sender → mute + scam

### Tier 2 — Repeated Forward Suppression (produces mute)
9. High forward count (≥5) + user muted similar → mute + forward
10. High forward count + user dismissed + no reply → mute + forward

### Tier 3 — Explicit Suppression (produces mute)
11. User opted-out + promotional content → mute + promotion
12. User muted similar + no urgency + not admin → mute + spam/promotion

### Tier 4 — Notify Conditions
13. Group admin + immediate time reference + no safety flags → notify + urgent
14. Deadline + trusted sender + no safety flags → notify + urgent/event
15. Verified business + active transaction + no domain mismatch + no safety flags → notify + business_update
16. Direct @mention + trusted/admin/reply history + immediate time reference → notify + urgent
17. Trusted personal contact + immediate time reference + no safety flags → notify + urgent
18. Waiting/leaving signal + trusted source → notify + urgent/business_update

### Tier 5 — Digest (useful but non-urgent)
20. Opted-in or verified business promotion (not opted-out) → digest + promotion
21. Future event date, no urgency → digest + event
22. Verified business non-urgent → digest + business_update
23. Harmless greeting → digest + greeting
24. Historical dismiss + no urgency + not admin → digest/mute + personal/promotion
25. Known sender + no safety flags → digest + personal

### Tier 6 — Default
26. Default → digest + unknown (confidence 0.60)

---

## 5. Safety Precedence

**Safety rules (Tier 1) always evaluate before urgency rules (Tier 4).**

Rationale:
- Fake urgency is common in scam messages.
- Business verification does NOT override safety signals.
- Known or trusted senders can still send scam content (forwarded scams).
- Prompt injection must be classified before any LLM-style processing.

---

## 6. Urgency Policy

A message may become `notify` only when:
- A real time constraint exists (minutes, specific clock time, today's event)
- The sender is trusted (admin, verified business with active transaction, known trusted contact)
- No safety flags are raised

Fake urgency (scam pressure, account-lock threats) does NOT produce notify.

---

## 7. Personalization Policy

Personalization signals used (in priority order):
1. `group_muted_by_user` — suppresses priority UNLESS admin + direct urgent mention
2. `historical_report_signal` — safety weight increase
3. `historical_mute_signal` — strong suppression weight
4. `historical_dismiss_signal` — moderate suppression weight
5. `user_opted_out` — blocks promotional content
6. `user_opted_in` — raises promotional content to digest
7. `user_has_active_transaction` — raises business_update confidence
8. `historical_reply_signal` — moderate confidence boost
9. `sender_is_group_admin` — moderate trust boost
10. `sender_trusted_personal` — personal conversation with reply history
11. `user_engagement_rate` — aggregate signal (supplemental only)

---

## 8. Evidence Selection Method

**Algorithm** (deterministic, no vector search):
1. Filter `message_history` to same `user_id` and `created_at` < message's `created_at`
2. Score candidates:
   - Same sender/business/group: +3/+2/+2
   - Behavioral events (reported=+3, muted=+2, dismissed=+1, replied=+1)
   - Keyword overlap: +1 per shared token (max +2)
3. Sort by score desc, then by recency desc
4. Return up to 3 IDs

**Constraints**:
- Only `message_0XXX` IDs (never `msg_*`)
- No future evidence
- No other user's events unless officially appropriate
- Deduplicated
- 'none' when no candidates

---

## 9. Media Fallback Behavior

**Images** (when OCR unavailable):
- Confirm file exists at path from `images.csv`
- Record `media_present=True`, `media_available=True/False`
- Use text context and metadata only
- Apply `confidence -= 0.04` when file exists but content unknown
- Reason does NOT claim visual content

**Voice notes** (when ASR unavailable):
- Confirm file exists at path from `voice_notes.csv`
- Record `media_present=True`, `media_available=True/False`
- Use any accompanying text and sender context
- Apply `confidence -= 0.04` when file exists but content unknown
- Reason does NOT claim spoken content

**Failure behavior**: Row is never dropped. Processing continues with text-and-metadata-only signals.

---

## 10. Confidence Method

Starting point: `confidence_base` from matched rule (range 0.60–0.92).

Adjustments (additive, clamped to [0.0, 1.0]):
| Condition | Adjustment |
| --- | --- |
| historical_reply_signal | +0.04 |
| historical_dismiss_signal on mute/digest | +0.03 |
| historical_report_signal on mute | +0.04 |
| business_is_verified on business decision | +0.02 |
| user_has_active_transaction on notify | +0.03 |
| domain_mismatch on scam | +0.03 |
| context_missing | -0.06 |
| media_present AND NOT media_available | -0.04 |
| low-rule match (base < 0.70) | -0.04 |

Final confidence is rounded to 2 decimal places and clamped to [0.0, 1.0].

Rationale: confidence reflects signal agreement, context completeness, and rule strength. It is NOT a calibrated probability — it is a transparent rule-based score for this baseline.

---

## 11. Reason Method

Reasons are generated from triggered rules, not from generic templates.

Every reason must:
- Reference the primary triggered rule signal
- Be consistent with both `action` and `message_type`
- Not claim unseen media content
- Not claim fabricated user preferences
- Be ≤200 characters
- Use natural language (not technical field names)

---

## 12. Failure Behavior

| Failure Type | Handling |
| --- | --- |
| Missing required CSV | Exit with error before processing |
| Missing required column | Exit with error before processing |
| Duplicate incoming message_id | Report and exit |
| Row processing error | Catch exception, output digest+unknown+0.50+none, log warning |
| Missing media file | Continue with confidence penalty, reason does not claim content |
| Missing context record | Set context_missing=True, apply confidence penalty |
| Invalid output row | Caught by post-processing validator |

---

## 13. Tests (Required)

- Safety rules (8 types)
- Notify rules (4 conditions)
- Digest rules (3 conditions)
- Mute rules (3 conditions)
- Personalization: opt-in vs opt-out, muted group, trusted vs unknown sender
- Evidence: valid IDs only, no incoming IDs, no future evidence, 'none' when empty
- Row integrity: order preserved, no duplicates, no drops
- Media fallback: broken file = row preserved, confidence penalty applied
- Output schema: all validator checks
- Anti-hardcoding: paraphrased scam still triggers mute+scam

---

## 14. Non-Goals

This baseline does NOT include:
- Multi-agent orchestration
- Vector database or semantic retrieval
- LLM, VLM, or ASR API calls
- Fine-tuning
- Complex state machines
- Final confidence calibration
- Final production prompts
- Production OCR or ASR integration
- Final submission predictions
- Message-ID-specific output maps
- Hidden-test-specific rules

---

## 15. Baseline Commands

```bash
# Run baseline pipeline
python -m code.baseline --input dataset/messages.csv --output outputs/baseline_output.csv --trace outputs/baseline_trace.json

# Run evaluation (solved samples only)
python -m code.evaluate --sample dataset/sample_messages.csv --input dataset/messages.csv --baseline-output outputs/baseline_output.csv --report evaluation/baseline_v1_report.json

# Run all tests
python -m pytest tests/ -v
```

---

## 16. Output Paths

| File | Purpose | Should NOT Overwrite |
| --- | --- | --- |
| `outputs/baseline_output.csv` | Candidate baseline output for all 110 messages | `dataset/output.csv` |
| `outputs/baseline_trace.json` | Debug trace with per-row feature/rule details | — |
| `evaluation/baseline_v1_report.json` | Metric report from evaluation harness | — |

---

## 17. Versioning

- **Version**: `baseline_v1`
- **Rules version**: deterministic-rule-set-v1
- **Dataset hashes**: see `evidence/dataset_audit_results.json`
- **No model calls**: 0 external API calls, 0 cost
