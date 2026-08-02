# Historical Evidence Defense

Retrieval Policy:
1. Cross-User Isolation: user_id matching is mandatory.
2. Temporal Cutoff: timestamp < incoming_message_timestamp.
3. Relevance Thresholding: Scores below threshold are omitted.
4. Honest none: 58/110 rows use none to prevent hallucinated historical links.
