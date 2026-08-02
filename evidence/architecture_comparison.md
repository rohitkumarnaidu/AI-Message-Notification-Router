# Architecture Comparison Matrix

**Scoring Scale**: 1 = poor, 2 = weak, 3 = acceptable, 4 = strong, 5 = excellent. (For Cost, Time, Failure surface: 5 = lowest cost/time/risk, 1 = highest cost/time/risk)

| Option | Requirement fit | Reliability | Personalization | Multimodal | Safety | Testability | Time | Cost | Failure surface | Interview defensibility | Total |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **A: Deterministic only** | 2 | 5 | 2 | 1 | 5 | 5 | 4 | 5 | 5 | 2 (rigid) | 36 |
| **B: Single LLM call** | 3 | 2 | 4 | 4 | 1 | 2 | 5 | 3 | 2 | 2 (unsafe) | 28 |
| **C: Deterministic + LLM Router** | 4 | 4 | 4 | 4 | 5 | 4 | 3 | 3 | 3 | 4 (balanced) | 38 |
| **D: Retrieval-augmented LLM** | 5 | 4 | 5 | 4 | 5 | 3 | 2 | 2 | 2 | 5 (comprehensive) | 37 |
| **E: Staged explicit workflow** | 5 | 5 | 5 | 4 | 5 | 4 | 1 | 2 | 3 | 5 (debuggable) | 39 |
| **F: Multi-agent** | 5 | 2 | 5 | 4 | 2 | 1 | 1 | 1 | 1 | 1 (overkill) | 23 |

## Options Detailed Analysis

### Option A — Deterministic pipeline only
* **Strengths:** 100% reliable output formatting, zero AI hallucinations, perfectly safe, zero inference cost.
* **Weaknesses:** Cannot read images (Multimodal=1). Fails at semantic understanding (Personalization=2, Requirement fit=2). Fails Phase 1 capability requirements.

### Option C — Deterministic pipeline plus bounded LLM router
* **Strengths:** Wraps a structured LLM call with deterministic safety gates. Solves semantic limitations while remaining safe.
* **Weaknesses:** Lacks rich historical retrieval (limits personalization).

### Option E — Explicit state-machine or staged workflow (Winner)
* **Description:** Validate -> Inspect Media -> Retrieve History -> Bounded LLM Reasoning -> Deterministic Policy Resolver -> Validate Output.
* **Strengths:** Highly debuggable, safely sandboxes the LLM, supports complex multimodal and retrieval requirements.
* **Time/Cost Risk:** Requires implementing multiple distinct stages, but components can be simplified.
* **Decision:** This represents the "Preferred default" from the prompt and is the most defensible architecture.

### Option F — Multi-agent
* **Fatal Weaknesses:** Agents for "Safety Analyst" and "Media Analyst" introduce non-deterministic loops, extreme latency, high failure surfaces, and violate the "simplest sufficient architecture" rule. Overengineering risk is critical.
