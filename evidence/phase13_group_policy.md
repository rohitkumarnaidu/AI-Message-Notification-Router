# Phase 13 Muted Groups and Mentions

- Implementation: `group_policy.py` checks group mute overrides.
- Default policy for muted group is digest or mute.
- Direct mention by an admin with no safety risks overrides the mute to notify.
- Operational urgency in muted groups overrides mute.
