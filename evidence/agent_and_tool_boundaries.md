# Agent and Tool Boundaries

## Architectural Stance
**No multi-agent swarm is used.** We are using a Staged Explicit Workflow (State Machine). There is one bounded LLM call to process text and contextual data, and separate calls to process media. 

## Tool Boundaries
There are **no dynamic tool-calling loops** (e.g., no ReAct loop). The LLM is NOT allowed to "decide" to call tools to browse the web or access the file system. 
Instead, data is retrieved deterministically in advance (Retrieval-Augmented Generation approach) and injected into the prompt.

### Bounded Limits
* **Call Limits:** Maximum 1 media extraction call per media file. Maximum 1 structured router call per message (with 1 retry on JSON validation failure).
* **Loop Limits:** 0 dynamic loops. Strictly sequential data flow.
* **Timeouts:** 10 seconds per LLM call.
* **Security Restrictions:** The LLM receives context as a raw text string. It has no network, shell, or file access.
* **Fallbacks:** If the single LLM reasoning pass fails or times out, the system falls back to the deterministic baseline policy.
