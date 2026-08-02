# Phase 17 Personalization Explanation: Contextual & User-Centric Routing

## Executive Overview
A core requirement of the WhatsApp Message Notification Router is **personalized routing**: the *exact same message content* must produce different actions (`notify`, `digest`, or `mute`) for different users depending on their individual context, preferences, relationships, and history.

Generic notification systems treat messages in isolation based solely on text content. In contrast, our system evaluates incoming content through a **user-specific context matrix** comprised of six distinct personalization axes:
1. **User Quiet Hours & Timezone**
2. **Notification Load & Fatigue Level**
3. **Group Membership & Mute Policies**
4. **Business Subscription State (Opt-In / Opt-Out)**
5. **Sender Relationship & Trusted Contact Hierarchy**
6. **Historical Behavioral Patterns (Reply, Mute, Dismiss, Report Ratios)**

---

## The 6 Personalization Axes Breakdown

### Axis 1: User Quiet Hours & Timezone (`code/temporal.py`, `code/quiet_load.py`)
Users configure quiet hours windows (e.g., `22:00-07:00`). 
* **Standard Policy**: Non-urgent messages during quiet hours are automatically downgraded from `notify` to `digest`.
* **Urgency Override**: Only verified **genuine urgency** (concrete immediate deadline, e.g., "waiting outside", "flight departing in 20 min") is permitted to break quiet hours and deliver a `notify`.

### Axis 2: Notification Load & Fatigue (`code/quiet_load.py`)
The system tracks daily notification volume and recent frequency.
* **High Load State** (`daily_notifications > 50` or `recent_notifications > 10`): Routine personal updates or transactional updates that would normally `notify` during low load are shifted to `digest` to prevent user cognitive overload.
* **Direct Mention Exemption**: Direct `@user` mentions or direct messages from trusted senders bypass high-load downgrades.

### Axis 3: Group Membership & Group Mute State (`code/group_policy.py`)
WhatsApp groups range from noisy family groups to critical work operational teams.
* **Muted Group Policy**: If a user has explicitly muted a group (`group_muted = True`), all standard group broadcasts are routed to `mute`.
* **Selective Admin Exception**: A message in a muted group is upgraded to `notify` *only* if it is a direct mention sent by a recognized **Group Admin** (`is_direct_mention and is_group_admin`). Standard direct mentions in muted groups route to `digest`.

### Axis 4: Business Subscription State (`code/safety_detectors.py`, `code/preclassifier.py`)
Commercial messages from business accounts (`business_id`) are evaluated against explicit user preferences (`business_opt_ins`, `business_opt_outs`).
* **Subscribed / Opted-In Business**: Operational updates or promotional offers from opted-in businesses route to `digest` (or `notify` if an active transaction deadline exists).
* **Opted-Out Business**: Promotional broadcasts from businesses the user has explicitly opted out of are immediately routed to `mute` (`opted_out_promotion`).

### Axis 5: Sender Relationship & Trust Hierarchy (`code/feature_extractor.py`, `code/safety_detectors.py`)
Senders are categorized into distinct trust tiers: `trusted_personal`, `known_sender`, `verified_business`, `unverified_business`, and `unknown_sender`.
* **Trusted Personal Senders**: Direct personal messages or photos from contacts on the user's `trusted_senders` list route to `notify`.
* **Unverified / Unknown Senders**: The exact same photo or greeting from an unknown sender routes to `digest` or `mute`.

### Axis 6: Historical Behavioral Patterns (`code/evidence_selector.py`, `code/safety_detectors.py`)
The system indexes historical message events (`message_events.csv`) per user:
* **High Report / Dismiss Ratio**: If a user routinely reports or dismisses messages from a particular sender or message pattern, matching incoming messages are routed to `mute`.
* **Active Engagement History**: If the user frequently replies to messages from a contact, confidence for `notify` is boosted.

---

## Comparative Personalization Matrix: Same Content, 3 Different Users

To demonstrate the depth of personalization, consider three different users receiving the **exact same incoming message**:

### Case Study 1: Promotional Broadcast
> **Incoming Message**: *"Flash Sale! Get 50% off all shoes today at ShoeKart. Use code FLASH50. Click https://shoekart.in/sale"*

| User Profile | Personalization Context | Resulting Action | Message Type | Reason |
|---|---|---|---|---|
| **User A** (Active Shopper) | Opted-in to ShoeKart (`business_opt_ins`), Normal load, Day time. | `digest` | `promotion` | Promotional content from a verified business the user is subscribed to, queued for digest. |
| **User B** (Unsubscribed) | Explicitly opted-out of ShoeKart (`business_opt_outs`). | `mute` | `promotion` | Promotional content from a business that the user has explicitly opted out of. |
| **User C** (Spam Target) | History of reporting ShoeKart broadcasts (`report_patterns > 0.8`), Muted history. | `mute` | `spam` | Sender has a consistent history of being reported and muted by the user. |

---

## Case Study 2: Operational Group Update
> **Incoming Message**: *"Guys, please review the event budget sheet by 5 PM today. Link: https://docs.google.com/sheet1"*

| User Profile | Personalization Context | Resulting Action | Message Type | Reason |
|---|---|---|---|---|
| **User A** (Active Member) | Active group member, Not muted, 2:00 PM local time. | `notify` | `urgent` | Time-sensitive operational update with concrete deadline from group chat. |
| **User B** (Quiet Hours) | Active group member, Not muted, Quiet hours active (23:30 local time). | `digest` | `event` | Non-emergency group update received during quiet hours, routed to digest for morning review. |
| **User C** (Muted Group) | Group is muted by user, Sender is not an admin, User not tagged. | `mute` | `business_update` | Message in a group explicitly muted by the user, suppressed from notification stream. |

---

## Case Study 3: Direct Personal Photo Message
> **Incoming Message**: *(Image attached: Photo of family dinner with text "Look who showed up!")*

| User Profile | Personalization Context | Resulting Action | Message Type | Reason |
|---|---|---|---|---|
| **User A** (Family Contact) | Sender is in `trusted_senders`, Direct 1-on-1 personal chat. | `notify` | `personal` | Personal photo message received from a recognized trusted contact. |
| **User B** (High Load User) | Sender is known, but User B has high notification load (>60 today). | `digest` | `personal` | Non-urgent personal media received during high notification load, queued for digest. |
| **User C** (Unknown Contact) | Sender is unknown (`sender_user_id` not in contacts), No prior message history. | `digest` | `unknown` | Unsolicited media message from an unknown sender without established relationship. |

---

## Code Implementation Traceability

The table below links each personalization decision rule directly to its underlying implementation in the codebase:

| Decision Rule | Source File | Function / Logic | Code Reference |
|---|---|---|---|
| Group Mute & Admin Exception | [`code/group_policy.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/group_policy.py#L1-L26) | `adjust_for_group_policy()` | Muted group -> `mute`; Admin mention -> `notify` |
| Quiet Hours Downgrade | [`code/quiet_load.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/quiet_load.py#L14-L28) | `adjust_for_quiet_hours()` | Quiet hours -> `digest` unless `is_genuine_urgency` |
| High Load Reduction | [`code/quiet_load.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/quiet_load.py#L30-L42) | `adjust_for_load()` | High load -> `digest` unless direct message/mention |
| Opted-out Business Suppression | [`code/preclassifier.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/preclassifier.py#L136-L142) | `preclassify_message()` | Opt-out -> `mute` / `promotion` |
| Historical Report Muting | [`code/safety_detectors.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/safety_detectors.py#L854-L858) | `extract_safety_signals()` | High report/mute history -> `mute` / `spam` |
| Evidence Grounding | [`code/evidence_selector.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/evidence_selector.py#L45-L88) | `select_evidence()` | Matches historical message events per user |

---

## Summary Statement
By grounding routing logic in explicit per-user contextual signals, our architecture ensures that notification decisions are tailored to each user's exact preferences, relationships, and schedule—delivering high precision without sacrificing user privacy or safety.
