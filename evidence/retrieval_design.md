# Retrieval Design

## Candidate Generation
Due to the small scope of the datasets, candidate generation uses lightweight deterministic filtering.
* **Filters:** Same receiving user AND (Same sender OR Same group OR Same business).

## Eligibility
* **Exclusions:**
  - Future history (timestamp must be older than incoming message).
  - Invalid message IDs.
  - Duplicate interactions.

## Ranking
* **Strategy:** Hybrid sorting based on:
  1. High-value behavior (e.g., `muted_after_message == 1` or `message_replied == 1` weighted highest).
  2. Recency (timestamp descending).
* **Limit:** Top 3 most relevant historical interactions.

## No-Evidence Behavior
* When no history matches, the retriever returns an empty list. The `evidence_message_ids` output is restricted to `[]` or valid IDs only. Fabricating an ID is explicitly forbidden by the output validator.

## Leakage Protections
* **Cross-user leakage:** Prevented by enforcing strict `user_id` matches on all historical lookups.
* **Future leakage:** Prevented by enforcing strict `created_at` timestamp comparison.
