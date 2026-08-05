import csv
from typing import List
from schemas import RouterDecision

# Load previous outputs to serve as mock LLM responses
mock_cache = {}
try:
    with open("outputs/output.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mock_cache[row["message_id"]] = row
except Exception as e:
    print(f"Mock provider warning: {e}")

class ProviderFallbackError(Exception): pass
class PolicyRejectionError(Exception):
    def __init__(self, reason: str):
        super().__init__(f"Provider policy rejection: {reason}")
        self.reason = reason

# A global state to hack getting the message ID since it's not in the prompt
# actually we can extract message_id from the evidence list or context if needed, 
# but it's easier to just patch router.py to pass the message_id to the provider.

# Wait, router.py does this: 
# llm_decision = generate_routing_decision(prompt, evidence_allowlist=valid_evidence_ids)
# It doesn't pass message_id. 

# Let's just create a simpler batch runner script that imports router, context_builder etc.
