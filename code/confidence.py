"""
Phase 15 Confidence Calibrator.
Applies grounded penalties and bounds confidence strictly to [0.00, 0.99].
Never assigns 1.0 automatically.
"""
from typing import Optional
from schemas import ConfidenceDecision, ExecutionMode

def calibrate_confidence(
    raw_confidence: float,
    execution_mode: ExecutionMode = ExecutionMode.DETERMINISTIC_DIRECT,
    is_deterministic: bool = True,
    has_fallback: bool = False,
    has_schema_repair: bool = False,
    has_conflict: bool = False,
    media_failed: bool = False
) -> ConfidenceDecision:
    """
    Computes calibrated confidence score based on decision signals and penalties.
    """
    fallback_penalty = 0.15 if has_fallback else 0.0
    schema_repair_penalty = 0.10 if has_schema_repair else 0.0
    conflict_penalty = 0.10 if has_conflict else 0.0
    media_penalty = 0.15 if media_failed else 0.0
    
    if is_deterministic:
        base = max(0.85, raw_confidence)
    else:
        base = raw_confidence

    total_penalty = fallback_penalty + schema_repair_penalty + conflict_penalty + media_penalty
    final_conf = max(0.30, min(0.99, base - total_penalty))
    
    # Audit 1.00 rule: Never allow 1.00
    if final_conf >= 1.0:
        final_conf = 0.99
        
    return ConfidenceDecision(
        raw_model_confidence=raw_confidence,
        deterministic_strength=0.95 if is_deterministic else 0.70,
        fallback_penalty=fallback_penalty,
        schema_repair_penalty=schema_repair_penalty,
        conflict_penalty=conflict_penalty,
        final_confidence=round(final_conf, 2),
        calibration_version="v15.0"
    )
