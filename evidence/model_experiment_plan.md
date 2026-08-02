# Model Experiment Plan

## Candidates
* Gemini 1.5 Flash (Preferred for high speed, low cost, multimodal capabilities, and native JSON mode).
* Gemini 1.5 Pro (Fallback for highly complex reasoning if Flash fails).

## Capabilities Required
* Native Structured Output (JSON Schema enforcement).
* Multimodal (images and audio if applicable).
* Prompt-injection resistance.

## Experiment Criteria
The model will be evaluated against the 30 solved samples to ensure it exceeds the Baseline's 70% accuracy. 

### Selected Model
**Gemini 1.5 Flash** is selected conditionally, pending Phase 5 implementation testing, because it is the cheapest and simplest model that supports structured outputs and multimodal ingestion.

## Unresolved Risks
* Local environment API limits or credential availability. If external API access is restricted during final execution, the deterministic baseline must serve as the ultimate fallback.
