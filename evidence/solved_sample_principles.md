# Phase 2 — Reusable Routing Principles

**Source**: Derived from `dataset/sample_messages.csv` (30 solved examples)
**Status Labels**:
- `OFFICIAL EXPECTED VALUE` — directly from solved sample output
- `DATA-SUPPORTED INFERENCE` — inferred from input context in official data
- `UNRESOLVED AMBIGUITY` — insufficient data to determine definitively

Do not hardcode these as lookup tables. These are generalizable routing rules.

---

## 1. notify Principles (9/30 solved samples)

### P-N1 — Same-Day Operational Deadline + Trusted Admin/Sender
- **Pattern**: Time-critical (minutes/hours), verified source (admin, coworker, trusted contact), user-specific impact.
- **Signal set**: Admin role in group + explicit time window + logistical impact on user.
- **Examples**: Water tanker leaving (sample_001), bus leaving early (sample_002), delivery today (sample_004).
- **Status**: OFFICIAL EXPECTED VALUE

### P-N2 — Direct User Mention (@mention) + Actionable Deadline
- **Pattern**: User is directly named or mentioned in a work or peer context with a required response.
- **Signal set**: @user_id match + coworker/friend sender + explicit time constraint.
- **Examples**: @u_010 prod review (sample_003), @u_004 cab count (sample_006).
- **Status**: OFFICIAL EXPECTED VALUE

### P-N3 — Verified Business + Active Transaction Match
- **Pattern**: Verified business sends status update that matches user's recent order/appointment/booking.
- **Signal set**: verified=1 + user_business_history has recent order/booking/payment + content semantically matches (delivery, appointment).
- **Examples**: Amazon delivery day (sample_004), health appointment today (sample_005).
- **Status**: OFFICIAL EXPECTED VALUE

### P-N4 — Close Contact Voice Note (Inferred Urgency from History)
- **Pattern**: Short voice note from trusted contact, user has rapid historical reply to same sender.
- **Signal set**: Trusted sender + fast `reaction_time_minutes` in history + voice modality.
- **Examples**: sample_042 (voice, notify, urgent, close contact + fast history).
- **Status**: DATA-SUPPORTED INFERENCE (voice content unknown)

### P-N5 — Work Emergency with Explicit Escalation Threshold
- **Pattern**: Coworker/colleague sends message with system-level urgency and explicit time until consequence.
- **Signal set**: Coworker sender + deadline stated as minutes/threshold + user history of fast replies.
- **Examples**: sample_051 (escalation in 20 mins).
- **Status**: OFFICIAL EXPECTED VALUE

---

## 2. digest Principles (11/30 solved samples)

### P-D1 — Useful Information Without Immediate Deadline
- **Pattern**: Message contains relevant information but action window is days not minutes.
- **Signal set**: No urgency language + optional action + non-admin sender or admin with multi-day window.
- **Examples**: Cultural night form open till Sunday (sample_008), market note (sample_053 in messages.csv).
- **Status**: OFFICIAL EXPECTED VALUE

### P-D2 — Opted-In Promotion or Business Update
- **Pattern**: Verified business sends promotion or update that user opted into receiving.
- **Signal set**: verified=1 + opted_in=1 in user_business_history + promotional content.
- **Examples**: Ladakh travel deal (sample_007), PVR feedback (sample_011).
- **Status**: OFFICIAL EXPECTED VALUE

### P-D3 — Harmless Greeting from Known Contact
- **Pattern**: Non-urgent, safe greeting with minor social value.
- **Signal set**: No safety signals + no urgency + sender known but not critical + user did not mute.
- **Examples**: Good morning family (sample_009), casual match chat (sample_010).
- **Status**: OFFICIAL EXPECTED VALUE

### P-D4 — Unknown Sender Without Risk or Urgency
- **Pattern**: First contact from unfamiliar sender but no scam signals, no credential requests, polite.
- **Signal set**: No user-sender history + no suspicious patterns + polite framing.
- **Examples**: Pottery workshop lost bottle (sample_049).
- **Status**: OFFICIAL EXPECTED VALUE

### P-D5 — Trusted Contact, Explicitly Not Urgent
- **Pattern**: Trusted sender explicitly states the message is not urgent.
- **Signal set**: Trusted sender + "nothing urgent" language + no deadline.
- **Examples**: sample_050 ("Don't call now, nothing urgent").
- **Status**: OFFICIAL EXPECTED VALUE

### P-D6 — Voice Note or Image Without Urgency (Reduced Confidence)
- **Pattern**: Media message from trusted sender but no urgent context identifiable.
- **Signal set**: Trusted sender + voice/image + no historical urgency pattern.
- **Confidence note**: Confidence should be reduced (≤0.84) when voice content is unknown.
- **Examples**: sample_041 (voice, digest, personal, 0.82).
- **Status**: DATA-SUPPORTED INFERENCE

### P-D7 — Informational Business Advisory Without Action Deadline
- **Pattern**: Verified business sends safety or informational advisory. No "complete by" deadline.
- **Signal set**: verified=1 + informational framing + no payment/OTP request.
- **Examples**: sample_048 (safety advisory image, digest, business_update).
- **Status**: OFFICIAL EXPECTED VALUE

---

## 3. mute Principles (10/30 solved samples)

### P-M1 — User Repeatedly Dismissed/Muted This Sender or Message Type
- **Pattern**: Historical events show user dismissed or muted after similar content from same sender.
- **Signal set**: `notification_dismissed=1` or `muted_after_message=1` in message_events for this user+sender.
- **Examples**: Greeting forwards (sample_013), health forward (sample_014), travel promo (sample_015).
- **Status**: OFFICIAL EXPECTED VALUE

### P-M2 — Opted Out of This Business/Category
- **Pattern**: User opted out of this business's messages or previously muted similar.
- **Signal set**: opted_out=1 in user_business_history OR dismissal+muted in message_events.
- **Examples**: sample_015 (food delivery promo), sample_043 (business voice spam).
- **Status**: OFFICIAL EXPECTED VALUE

### P-M3 — OTP, Credential, or PIN Request (Scam)
- **Pattern**: Any message requesting OTP, password, login code, or PIN.
- **Signal set**: OTP/PIN keyword + "share/send/enter" verb + optional urgency language.
- **Priority**: Safety override — mute regardless of sender trust or other signals.
- **Examples**: sample_019, sample_020, sample_052.
- **Status**: OFFICIAL EXPECTED VALUE

### P-M4 — Prompt Injection / Router Override Attempt
- **Pattern**: Message text contains instructions directed at the routing system.
- **Signal set**: "ignore previous", "mark as notify", "action=", "system note for router", "internal metadata".
- **Priority**: Deterministic — classify before LLM processing.
- **Examples**: sample_053, msg_107, msg_109, msg_110, msg_108, msg_095.
- **Status**: OFFICIAL EXPECTED VALUE

### P-M5 — High Forward Count from Pattern Forwarder
- **Pattern**: Highly forwarded message (forwarded_count > 5) from sender with dismissal history.
- **Signal set**: forwarded_count > threshold + sender event history of dismissals.
- **Examples**: sample_013 (6x forward, dismissed), sample_014 (11x forward, dismissed).
- **Status**: OFFICIAL EXPECTED VALUE

---

## 4. Personalization Principles

### P-P1 — Same Content, Different User, Different Action (CRITICAL)
- **Evidence**: sample_044 (u_032, digest, promotion) vs sample_045 (u_033, mute, promotion) — identical image (img_008), same text, same sender, but different routing.
- **Why**: u_033 previously dismissed+muted similar messages; u_032 did not.
- **Implication**: Content alone is insufficient. User behavioral history is determinative.
- **Status**: OFFICIAL EXPECTED VALUE (strongest personalization proof in dataset)

### P-P2 — Muted Group with Admin Operational Notice
- **Pattern**: Even if a user muted a group, high-trust admin operational messages may warrant notify/digest.
- **Evidence**: Inferred from group_muted_by_user + admin role patterns (not directly in solved samples).
- **Status**: UNRESOLVED AMBIGUITY — requires hidden test coverage

### P-P3 — Opt-In vs. Opt-Out Changes Business Message Routing
- **Evidence**: Opted-in promotion → digest (sample_007); opted-out or dismissed → mute (sample_015, sample_043).
- **Status**: OFFICIAL EXPECTED VALUE

---

## 5. Safety Principles

### P-S1 — Scam Risk Overrides Engagement History
- Any safety risk (OTP request, account-block threat, suspicious link) must result in mute regardless of sender trust or user engagement history.
- **Status**: OFFICIAL EXPECTED VALUE

### P-S2 — Urgency Language Is Not Proof of Legitimacy
- Messages using "URGENT", "immediately", "before lock" are not automatically notify.
- Verify sender trust + domain match + content type first.
- **Status**: DATA-SUPPORTED INFERENCE (multiple scam samples use urgency language)

### P-S3 — Unverified Business Domain = Lower Trust
- `domain_used_by_sender != official_domain` + `domain_used_by_sender_age_days < 30` = scam indicator.
- **Status**: DATA-SUPPORTED INFERENCE from business_accounts.csv schema

### P-S4 — Prompt Instructions Inside Message Are Untrusted
- The routing system must treat all message content as untrusted input data.
- **Status**: OFFICIAL EXPECTED VALUE (sample_053 demonstrates this explicitly)

---

## 6. Anti-Hardcoding Reminder

> These principles are generalizable. They must NOT be implemented as:
> - Lookup tables from message_id to action
> - Hardcoded sample_msg_* conditions
> - Full sample text strings embedded in code
> - Evidence IDs hardcoded for specific known inputs
>
> A robust system must respond to changed context (different user, different sender, different deadline, different history).
