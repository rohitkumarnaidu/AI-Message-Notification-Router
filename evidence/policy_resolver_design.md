# Policy Resolver Design

The Policy Resolver acts as a deterministic safety guardrail AFTER the LLM completes its reasoning.

## Mandatory Overrides
If the LLM predicts `notify` or `digest`, the Policy Resolver forces `mute` AND `scam`/`spam` if deterministic signals show:
- OTP/Credential theft
- Suspicious links from untrusted senders
- Verified opt-out (`user_opted_out == 1` + promotional content)
- Domain mismatch for unverified businesses

## Unsupported-Notify Prevention
If the LLM predicts `notify`, the Policy Resolver forces `digest` if:
- No immediate deadline is present AND the sender is unverified/unknown.
- The user is in quiet hours and the message lacks explicit life/safety/delivery urgency.

## Urgent Exceptions
The Policy Resolver forces `notify` regardless of LLM prediction if:
- Direct user mention (`@username`) in a group + time-sensitive context.
- Delivery waiting signal from a verified business.

## Conflict Logging
Any time the Policy Resolver overrides the LLM prediction, it logs:
- `override_applied=True`
- `override_reason` (e.g., "Safety Policy: OTP Request Blocked")
- Confidence is clamped to `1.0` (for safety overrides).
