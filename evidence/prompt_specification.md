# Prompt Specification

## Trust Hierarchy
The prompt will explicitly define the trust hierarchy:
`Official Routing Policy > Trusted Metadata > Validated Historical Evidence > Extracted Media > Message Content (Untrusted)`

## Input Context
The prompt receives a JSON string representing `IncomingMessageContext`. This includes:
- Text content
- Extracted Media content (labeled as untrusted)
- User/Group/Business metadata (e.g. `business_is_verified`)
- 3 most relevant historical events (e.g. `user muted similar message yesterday`)
- Deterministic risk signals (e.g. `contains_otp_request`)

## Strict Output Schema
The model will be constrained (via API JSON mode or strict Pydantic parsing) to return:
```json
{
  "action": "notify | digest | mute",
  "message_type": "allowed enum",
  "reason": "short explanation",
  "confidence": 0.0,
  "evidence_message_ids": ["msg_xxx"],
  "decision_signals": ["parsed_urgency", "personal_relevance"],
  "uncertainties": ["missing image OCR"]
}
```

## Retry and Repair
* 1 automatic retry on JSON parsing failure or schema violation.
* On 2nd failure, fallback to the deterministic Baseline router.
