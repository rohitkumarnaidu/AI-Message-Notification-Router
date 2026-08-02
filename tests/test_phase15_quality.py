import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))

from schemas import (
    EvidenceDecision,
    ReasonDecision,
    ConfidenceDecision,
    ReleaseCandidateManifest,
    ExecutionMode
)
from confidence import calibrate_confidence

def test_confidence_calibration_default():
    conf_dec = calibrate_confidence(raw_confidence=0.95, is_deterministic=True)
    assert conf_dec.final_confidence <= 0.99
    assert conf_dec.final_confidence >= 0.85
    assert conf_dec.calibration_version == "v15.0"

def test_confidence_calibration_penalties():
    conf_dec = calibrate_confidence(
        raw_confidence=0.90,
        is_deterministic=False,
        has_fallback=True,
        has_schema_repair=True,
        has_conflict=True,
        media_failed=True
    )
    # Total penalties: 0.15 + 0.10 + 0.10 + 0.15 = 0.50
    assert conf_dec.fallback_penalty == 0.15
    assert conf_dec.schema_repair_penalty == 0.10
    assert conf_dec.final_confidence == 0.40

def test_confidence_calibration_never_one():
    conf_dec = calibrate_confidence(raw_confidence=1.0, is_deterministic=True)
    assert conf_dec.final_confidence < 1.0
    assert conf_dec.final_confidence == 0.99

def test_release_manifest_schema():
    manifest = ReleaseCandidateManifest(
        candidate_path="outputs/phase15_release_candidate.csv",
        candidate_hash="abc123hash",
        freeze_status="FROZEN"
    )
    assert manifest.freeze_status == "FROZEN"
    assert manifest.router_version == "v15.0"
