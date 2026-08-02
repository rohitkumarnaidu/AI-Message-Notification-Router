# Structured Output & Schema Reliability

Schema Enforcement:
- Pydantic models (RouterProposal, FinalRouterDecision).
- Strict enums for action (notify, digest, mute) and 11 message types.
- 1-shot self-repair for malformed JSON before deterministic fallback.
