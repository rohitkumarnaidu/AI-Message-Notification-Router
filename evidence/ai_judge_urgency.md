# AI Judge Defense: Urgency Disambiguation, Quiet Hours & Group Policies

This document details the architectural mechanisms in [`code/temporal.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/temporal.py), [`code/quiet_load.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/quiet_load.py), [`code/group_policy.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/group_policy.py), and [`code/interruption_resolver.py`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/interruption_resolver.py) that handle urgency reasoning, quiet hours enforcement, and group conversation policies.

---

## 1. Concrete Deadlines vs. Vague Urgency & Marketing Lures

A primary failure mode of basic notification routers is treating all urgent-sounding language equally. Marketing campaigns ("URGENT SALE ENDS TODAY", "Hurry before stock runs out!") and phishing lures ("Act immediately to unlock account") use artificial urgency to force user clicks. Real emergencies contain concrete time constraints ("Flight departs in 45 minutes", "Delivery agent waiting outside").

### Implementation Defense
Implemented in [`safety_detectors.py:L503-L560`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/safety_detectors.py#L503-L560) and [`temporal.py:L7-L44`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/temporal.py#L7-L44):

```python
# Concrete, time-bound deadlines (Self-verifying)
_CONCRETE_DEADLINE_PATTERNS = [
    re.compile(r'\b(today|tonight|this\s+morning|this\s+evening|by\s+\d+\s*(am|pm))\b', re.IGNORECASE),
    re.compile(r'\b(in\s+\d+\s*(minute|hour|min|hr)s?)\b', re.IGNORECASE),
    re.compile(r'\b\d{1,2}[:\-]\d{2}\s*(am|pm)?\b', re.IGNORECASE),
    re.compile(r'\bwaiting\s+(for\s+you|outside|downstairs|at\s+the\s+door)\b', re.IGNORECASE),
    re.compile(r'\b(flight|train|bus|delivery)\s+(is\s+)?(arriving|leaving|departing|here)\b', re.IGNORECASE),
    re.compile(r'\b(last\s+day|final\s+notice|deadline\s+(is\s+)?(today|tomorrow|now))\b', re.IGNORECASE),
]

# Vague, manipulative urgency (Not self-verifying)
_VAGUE_URGENCY_PATTERNS = [
    re.compile(r'\b(urgent|urgently|emergency|asap|immediately|right\s*now)\b', re.IGNORECASE),
    re.compile(r'\b(jaldi|turant|abhi|fauran)\b', re.IGNORECASE),
    re.compile(r'\b(don\'?t\s+delay|hurry|rush)\b', re.IGNORECASE),
]
```

### Disambiguation Logic
1. **Concrete Deadlines (`has_concrete=True`)**: Indicates a real-time operational constraint. Grounded source confidence is set to `0.80` with `trusted=True`.
2. **Vague Urgency (`has_vague=True`, `has_concrete=False`)**: Indicates subjective or artificial pressure. Grounded source confidence is lowered to `0.55` with `trusted=False`.
3. **Fake Urgency Rejection**: In [`unsafe_notify_validator.py:L117-L122`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/unsafe_notify_validator.py#L117-L122), messages with vague urgency lacking concrete deadlines or trusted sender relationship are flagged as `is_fake_urgency`. Any proposed `notify` action is automatically downgraded to `digest`.

---

## 2. Quiet Hours Behavior & Policy Downgrades

Quiet hours prevent non-critical notifications from disturbing the user during sleep or focus windows.

### Window Definition & Machine Time Detachment
In [`temporal.py:L18-L26`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/temporal.py#L18-L26), quiet hours are evaluated relative to the message's `created_at` timestamp in local user time (defaulting to 22:00 / 10 PM through 07:00 / 7 AM):

```python
dt = datetime.fromisoformat(message_timestamp.replace('Z', '+00:00'))
hour = dt.hour
if hour >= 22 or hour < 7:
    ctx.is_quiet_hours = True
```

### Quiet Hours Resolution Rules
Implemented in [`quiet_load.py:L14-L28`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/quiet_load.py#L14-L28) and [`safety_policy.py:L308-L315`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/safety_policy.py#L308-L315):

```python
def adjust_for_quiet_hours(temporal_ctx: TemporalContext, is_genuine_urgency: bool, current_action: str) -> str:
    if temporal_ctx.is_quiet_hours:
        # Genuine urgency overrides quiet hours
        if is_genuine_urgency:
            return current_action
        
        # Downgrade routine notifications
        if current_action == "notify":
            return "digest"
            
    return current_action
```

- **Routine Notifications**: Non-urgent `notify` actions (e.g. personal greetings, routine updates) are automatically downgraded to `digest`.
- **Genuine Urgency Override (Priority 5)**: In [`safety_policy.py:L274-L286`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/safety_policy.py#L274-L286), if a message from a trusted contact or recognized group admin contains a **concrete immediate deadline**, the `notify` action is preserved across quiet hours.

---

## 3. Muted Group Policy & Direct Mention Exceptions

Group chats produce high volumes of noise. Users frequently set group conversations to `is_group_muted = True`.

### Policy Implementation
Implemented in [`group_policy.py:L1-L25`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/group_policy.py#L1-L25):

```python
def adjust_for_group_policy(
    is_group: bool,
    is_group_muted: bool,
    is_direct_mention: bool,
    is_group_admin: bool,
    current_action: str
) -> str:
    if not is_group:
        return current_action
        
    if is_group_muted:
        # Default muted group action
        new_action = "mute"
        
        # Exception 1: Direct @mention by Group Admin -> NOTIFY
        if is_direct_mention and is_group_admin:
            new_action = "notify"
            
        # Exception 2: Standard direct @mention by non-admin -> DIGEST
        elif is_direct_mention:
            new_action = "digest"
            
        return new_action
        
    return current_action
```

### Policy Precedence Rules
1. **Standard Chat in Muted Group**: Routed to `mute`.
2. **Direct `@mention` by Non-Admin**: Upgraded from `mute` to `digest`. Ensures the user is informed without loud acoustic interruptions.
3. **Direct `@mention` by Recognized Group Admin**: Upgraded from `mute` to `notify`. Group admins possess operational authority over group context, requiring immediate delivery for direct mentions.

---

## 4. Notification Load Throttling

When notification load is high (`daily_notifications > 50` or `recent_notifications > 10`), [`quiet_load.py:L30-L41`](file:///c:/Hackathons/Hackerrank/Message%20Notification%20Router/hackerrank-orchestrate-august26/code/quiet_load.py#L30-L41) throttles incoming notifications:

```python
def adjust_for_load(load_status: str, relevance: RelevanceSignals, current_action: str) -> str:
    if load_status == "high" and current_action == "notify":
        # Direct personal messages and mentions pass through
        if relevance.direct_message or relevance.direct_mention:
            return current_action
        # Broadcast/business notifications downgraded to digest
        return "digest"
    return current_action
```

High notification load protects user attention by batching routine broadcast updates into `digest` while preserving real-time `notify` channels for direct personal communications.
