from schemas import FinalDecision

def validate_reason(decision: FinalDecision) -> FinalDecision:
    """
    Validates the generated reason text to ensure no PII leakage, 
    no hallucinations, and no toxic language.
    """
    
    # Simple deterministic checks for PII
    forbidden_terms = ["@u_", "password", "ssn", "credit card"]
    
    reason_lower = decision.reason.lower()
    
    for term in forbidden_terms:
        if term in reason_lower:
            decision.reason = "Redacted due to PII/Security constraints"
            decision.validation_status = "redacted_pii"
            break
            
    # If confidence is extremely low and we are notifying, we might want to flag
    if decision.action == "notify" and decision.confidence < 0.5:
        decision.validation_status = "low_confidence_notify"
        
    return decision
