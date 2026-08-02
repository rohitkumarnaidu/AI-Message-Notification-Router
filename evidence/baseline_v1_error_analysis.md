# Baseline v1 Error Analysis

This document analyzes the 30% error rate (Action Accuracy = 70%) observed in the `baseline_v1` deterministic evaluation. 

## Action Misclassifications (9 Errors)

The baseline misclassified 9 out of 30 messages on the primary `action` routing objective.

### 1. `notify` predicted as `digest` (5 occurrences)
This is the most common failure mode. The baseline's deterministic rules for `notify` require rigid combinations (e.g., explicit deadlines, verified businesses + active transactions, explicit time phrases like "urgent", "now"). 
* **Failure Reason**: Semantic deadlines and implicit urgency are missed. A message might contain a time-sensitive issue or require human attention, but lack the exact regex triggers.
* **Example**: "The verified business message is legitimate but does not require immediate attention." (sample_msg_005) - The baseline couldn't discern the implicit urgency of the context without regex hits, falling back to a `digest` `business_update`.
* **Example**: "The message contains a future event or deadline that can be reviewed later." (sample_msg_004, sample_msg_006) - The baseline detected an event but misjudged its immediate relevance or urgency because it didn't strictly match the "immediate" time phrase regex.

### 2. `mute` predicted as `digest` (2 occurrences)
* **Failure Reason**: Promotions that lack explicit "discount", "offer", or "% off" keywords bypass the `promotion` regex, causing them to fall into `digest`.
* **Example**: "The promotion is from a verified business and the user has not opted out." (sample_msg_015) - A spam/scam or high-volume promotion was routed to digest because the safety/opt-out gates failed to trigger.
* **Example**: "The sender is known and the message does not contain safety risks or urgent action." (sample_msg_019) - The baseline couldn't infer that the sender's behavior was abusive or promotional without strict rule triggers.

### 3. `digest` predicted as `notify` (1 occurrence)
* **Failure Reason**: A false positive on urgency signals.
* **Example**: "A trusted contact sent an immediate request requiring a quick response." (sample_msg_050) - A message contained an urgency keyword (e.g., "now", "today") but was actually a casual or non-urgent statement.

### 4. `digest` predicted as `mute` (1 occurrence)
* **Failure Reason**: Overly aggressive historical rules.
* **Example**: "The user has previously muted messages similar to this one." (sample_msg_044) - A user previously muted a message from this sender, causing the baseline to aggressively mute a new message that was actually useful/harmless.

## Type Misclassifications

Type accuracy was only 43.3%. This is expected, as regex-based topic modeling is highly brittle.
* **Urgent vs Personal / Event**: The baseline struggles to differentiate between a casual mention of a time ("Let's meet tomorrow" - `event`/`personal`) and a true deadline ("Submit the form tomorrow" - `urgent`).
* **Scam vs Spam**: Safety gates caught scammers (e.g., OTP phishing), but distinguishing between malicious `scam` and annoying `spam` relies on nuanced tone that regex cannot easily capture.
* **Business Update vs Promotion**: Subtle upselling disguised as an update (e.g., "Your flight is booked! Upgrade to first class for $50") confuses the deterministic rule engine.

## Media Fallback Issues

Several errors note: *"Media content was unavailable for analysis, reducing confidence."*
* Since the deterministic baseline does not perform OCR on images or ASR on voice notes, it loses critical information for multimodal messages.
* E.g., A poster image might contain "50% OFF TODAY", but the text caption is just "Check this out!". The baseline sees no promotion keywords in the text and misclassifies it.

## Limitations to Address in ML Models
1. **Semantic Understanding**: Transition from rigid regex rules to LLM-based intent recognition to capture implied urgency, passive-aggressive tones, and nuanced promotions.
2. **Multimodal Processing**: Implement Gemini/Vision API to extract text and context from images and audio.
3. **Soft Weighting vs Hard Rules**: Rather than a rigid rule hierarchy where the first match wins, an LLM can balance conflicting signals (e.g., high historical engagement vs. a slightly promotional tone).
