# AI Judge Personalization & User-Centric Routing

## Executive Overview

A critical design requirement of the WhatsApp Message Notification Router is **personalized routing**. Generic notification systems process messages in isolation based solely on text content. In contrast, our system recognizes that the *exact same message content* must yield different actions (`notify`, `digest`, or `mute`) for different receiving users depending on their individual schedule, notification load, group mute preferences, business opt-in status, sender relationship, and interaction history.

This document details the **9 core personalization axes** built into the system and presents concrete, non-sensitive case study examples demonstrating how identical incoming messages produce tailored routing decisions.

---

## The 9 Personalization Axes

### 1. Receiving-User Isolation
* **Source Module**: [code/evidence_selector.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/evidence_selector.py#L35-L60), [code/context_builder.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/context_builder.py#L25-L60)
* **Mechanism**: Every incoming message is strictly evaluated in the isolated context of the `receiving_user_id`. When retrieving historical evidence or past interaction events, candidate records must satisfy `history_user_id == target_user_id`.
* **Impact**: User A's past mute/report history or quiet hours never leak into or influence User B's routing decisions (0 cross-user leaks).

### 2. Direct 1-on-1 vs Group Conversation Mode
* **Source Module**: [code/feature_extractor.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/feature_extractor.py#L50-L90), [code/relevance.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/relevance.py#L20-L45)
* **Mechanism**: Direct 1-on-1 messages from known personal contacts carry higher personal relevance scores than multi-user group chat broadcasts.
* **Impact**: Routine personal messages in 1-on-1 chats default to `notify` (during active hours), whereas routine group chat updates default to `digest` to prevent group chatter overload.

### 3. User Mentions (`@username`)
* **Source Module**: [code/relevance.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/relevance.py#L40-L65), [code/group_policy.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/group_policy.py#L1-L26)
* **Mechanism**: The system inspects message text for explicit tags (`@username` or `@UserFullName`).
* **Impact**: A direct `@user` mention elevates an informational group message from `digest` to `notify` or preserves notification status under high notification load.

### 4. Group Mute State & Admin Exception Policy
* **Source Module**: [code/group_policy.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/group_policy.py#L1-L26)
* **Mechanism**: Evaluates group mute configuration (`group_muted = True`) against sender authority (`is_group_admin`) and mention presence (`is_direct_mention`).
* **Impact**:
  * If a group is muted, standard broadcasts route to `mute`.
  * If a regular member tags the user in a muted group, it routes to `digest`.
  * If a recognized **Group Admin** directly tags the user in a muted group, it is upgraded to `notify`.

### 5. Business Subscription State (Opt-In / Opt-Out)
* **Source Module**: [code/preclassifier.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/preclassifier.py#L136-L142), [code/safety_detectors.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/safety_detectors.py#L320-L360)
* **Mechanism**: Cross-references business accounts (`business_id`) against per-user lists (`business_opt_ins`, `business_opt_outs`).
* **Impact**:
  * Subscribed/Opted-in business promotions route to `digest`.
  * Promotional broadcasts from opted-out businesses are immediately routed to `mute`.

### 6. Active Orders & Transaction Tracking
* **Source Module**: [code/relevance.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/relevance.py#L70-L85), [code/temporal.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/temporal.py#L40-L75)
* **Mechanism**: Detects active order tracking numbers, delivery OTPs, or active driver arrivals.
* **Impact**: Messages linked to an active delivery or order in progress override quiet hours or business promotion muting, routing directly to `notify`.

### 7. Historical Behavioral Patterns & Engagement
* **Source Module**: [code/evidence_selector.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/evidence_selector.py#L45-L88), [code/safety_detectors.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/safety_detectors.py#L854-L858)
* **Mechanism**: Aggregates past user actions from `message_events.csv` (reply count, mute count, dismiss count, report count).
* **Impact**: Senders or message patterns with high report/dismiss ratios (`report_ratio > 0.5`) are automatically suppressed to `mute`, while frequently replied contacts receive priority routing.

### 8. Quiet Hours & Timezone Window
* **Source Module**: [code/temporal.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/temporal.py#L1-L50), [code/quiet_load.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/quiet_load.py#L14-L28)
* **Mechanism**: Converts timestamp (`created_at`) to receiving user local timezone and checks if it falls inside `quiet_hours_start` and `quiet_hours_end` (e.g. 22:00 to 07:00).
* **Impact**: Non-emergency messages arriving during quiet hours are downgraded from `notify` to `digest`. Only verified **genuine urgency** (concrete immediate deadlines) breaks quiet hours.

### 9. Daily Notification Load & Cognitive Fatigue
* **Source Module**: [code/quiet_load.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/quiet_load.py#L30-L42)
* **Mechanism**: Tracks daily notification count (`daily_notifications`). If `daily_notifications > 50` (high load state), non-critical notifications are throttled.
* **Impact**: Routine informational updates that would normally notify during low load are shifted to `digest`, preserving `notify` strictly for direct personal alerts and `@mentions`.

---

## Concrete Case Study Examples

Below are four non-sensitive case studies showing how the **exact same incoming message** produces different routing actions for three different receiving users.

### Case Study 1: Commercial Promotional Offer
> **Incoming Message**: *"Weekend Mega Sale! Get 40% off on all footwear at StyleKart. Use code STYLESALE40 at checkout. https://stylekart.in/sale"*

| Receiving User | User Profile & Personalization Context | Assigned Action | Message Type | Grounded Routing Reason |
|---|---|---|---|---|
| **User 101 (Subscribed)** | Opted-in to StyleKart notifications (`business_opt_ins`), normal load, 2:15 PM local time. | `digest` | `promotion` | Promotional offer from a verified business the user is subscribed to, queued for daily digest. |
| **User 102 (Opted-Out)** | Explicitly opted-out of StyleKart communications (`business_opt_outs`). | `mute` | `promotion` | Promotional content from a commercial business account that the user has explicitly opted out of. |
| **User 103 (High Report Ratio)** | History of reporting StyleKart broadcasts (`report_ratio = 0.85`), muted history. | `mute` | `spam` | Sender matches historical pattern of messages frequently reported and muted by the user. |

---

### Case Study 2: Operational Group Update
> **Incoming Message**: *"Team, please complete the quarterly project status update in the shared sheet by 5:00 PM today. Sheet link: https://docs.google.com/sheet1"*

| Receiving User | User Profile & Personalization Context | Assigned Action | Message Type | Grounded Routing Reason |
|---|---|---|---|---|
| **User 201 (Active Member)** | Active group member, group not muted, 1:30 PM local time (active hours). | `notify` | `urgent` | Time-sensitive operational work update with a concrete 5:00 PM deadline today. |
| **User 202 (Quiet Hours)** | Active group member, group not muted, 11:15 PM local time (quiet hours active: 22:00-07:00). | `digest` | `event` | Non-emergency group update received during user quiet hours, queued for morning digest review. |
| **User 203 (Muted Group)** | Group is muted by user (`group_muted = True`), sender is regular member, user not tagged. | `mute` | `business_update` | Message in a group explicitly muted by the user, suppressed from notification stream. |

---

### Case Study 3: Direct Mention in Muted Group Chat
> **Incoming Message**: *"@Alice please verify the deployment logs for server-02 immediately before the client demo."*

| Receiving User | User Profile & Personalization Context | Assigned Action | Message Type | Grounded Routing Reason |
|---|---|---|---|---|
| **Alice (Admin Tag)** | Muted group, tagged directly (`@Alice`), sender is recognized **Group Admin**. | `notify` | `urgent` | Direct mention by a Group Admin in a muted group regarding an urgent operational issue. |
| **Alice (Member Tag)** | Muted group, tagged directly (`@Alice`), sender is a **Regular Member** (not Admin). | `digest` | `urgent` | Direct mention in a muted group sent by a non-admin member, routed to digest to avoid interruption. |
| **Bob (Untagged Member)** | Muted group, Bob is NOT tagged in the message. | `mute` | `business_update` | Message in a muted group without a direct mention for the receiving user. |

---

### Case Study 4: Order Delivery Tracking Alert
> **Incoming Message**: *"Your order #98214 is out for delivery. Driver Ramesh is arriving in 15 mins. Call +919876543210 for directions."*

| Receiving User | User Profile & Personalization Context | Assigned Action | Message Type | Grounded Routing Reason |
|---|---|---|---|---|
| **User 401 (Order Owner)** | Has active order #98214 in progress, quiet hours active (11:00 PM), verified delivery. | `notify` | `delivery` | Active delivery alert with concrete 15-minute arrival time overriding quiet hours. |
| **User 402 (High Load User)** | Has active order #98214, high notification load today (65 notifications delivered). | `notify` | `delivery` | High personal relevance active order delivery alert exempt from daily load throttling. |
| **User 403 (No Active Order)** | No active order in system history, sender unknown commercial ID. | `digest` | `promotion` | Unsolicited delivery broadcast without matching active order in user history. |

---

## Personalization Implementation Summary

The table below maps each personalization axis directly to its primary source file and method implementation:

| Personalization Axis | Primary Implementation File | Key Function / Method | Execution Behavior |
|---|---|---|---|
| **1. Receiving-User Isolation** | [code/evidence_selector.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/evidence_selector.py#L35-L60) | `select_evidence()` | Enforces `history_user_id == target_user_id` |
| **2. Direct vs Group** | [code/feature_extractor.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/feature_extractor.py#L50-L90) | `extract_features()` | Sets `is_group` and conversation type scores |
| **3. Direct Mentions** | [code/relevance.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/relevance.py#L40-L65) | `extract_relevance_signals()` | Extracts `@username` and name tags |
| **4. Group Mute & Admin** | [code/group_policy.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/group_policy.py#L1-L26) | `adjust_for_group_policy()` | Muted group -> `mute`; Admin tag -> `notify` |
| **5. Business Opt-In/Opt-Out** | [code/preclassifier.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/preclassifier.py#L136-L142) | `preclassify_message()` | Opt-out -> `mute`/`promotion`; Opt-in -> `digest` |
| **6. Active Orders** | [code/relevance.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/relevance.py#L70-L85) | `extract_relevance_signals()` | Active order ID match -> High priority `notify` |
| **7. Behavioral History** | [code/safety_detectors.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/safety_detectors.py#L854-L858) | `extract_safety_signals()` | High report/dismiss ratio -> `mute`/`spam` |
| **8. Quiet Hours** | [code/quiet_load.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/quiet_load.py#L14-L28) | `adjust_for_quiet_hours()` | Quiet hours -> `digest` unless genuine urgency |
| **9. Notification Load** | [code/quiet_load.py](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/quiet_load.py#L30-L42) | `adjust_for_load()` | High load (>50/day) -> `digest` unless direct tag |
