import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))

from schemas import TemporalContext, RelevanceSignals, SafetySignals
from temporal import extract_temporal_context, check_genuine_urgency
from relevance import extract_relevance_signals
from quiet_load import evaluate_notification_load, adjust_for_quiet_hours, adjust_for_load
from group_policy import adjust_for_group_policy
from interruption_resolver import resolve_interruption

def test_temporal_genuine_urgency():
    ctx1 = extract_temporal_context("My flight is in 2 hours", "2026-08-01T10:00:00Z")
    assert check_genuine_urgency(ctx1, "My flight is in 2 hours") == True
    
    ctx2 = extract_temporal_context("This is urgent please respond", "2026-08-01T10:00:00Z")
    assert check_genuine_urgency(ctx2, "This is urgent please respond") == False

def test_quiet_hours():
    ctx = TemporalContext(is_quiet_hours=True)
    # Genuine urgency should override quiet hours
    assert adjust_for_quiet_hours(ctx, True, "notify") == "notify"
    # Normal notify should digest in quiet hours
    assert adjust_for_quiet_hours(ctx, False, "notify") == "digest"

def test_notification_load():
    rel = RelevanceSignals(direct_message=True)
    # Direct message should bypass high load
    assert adjust_for_load("high", rel, "notify") == "notify"
    
    rel2 = RelevanceSignals(direct_message=False)
    # Standard broadcast should downgrade to digest under high load
    assert adjust_for_load("high", rel2, "notify") == "digest"

def test_group_policy():
    # Admin mentioning someone in a muted group
    assert adjust_for_group_policy(True, True, True, True, "notify") == "notify"
    # Regular message in muted group
    assert adjust_for_group_policy(True, True, False, False, "notify") == "mute"

def test_interruption_resolver():
    t_ctx = TemporalContext(is_quiet_hours=True)
    rel = RelevanceSignals()
    safety = SafetySignals()
    
    decision = resolve_interruption(
        proposed_action="notify",
        message_type="personal",
        temporal_ctx=t_ctx,
        relevance=rel,
        safety_signals=safety,
        notification_load="normal",
        is_group=False,
        is_group_muted=False,
        is_group_admin=False
    )
    
    # Due to quiet hours and no genuine urgency, it should digest
    assert decision.final_action == "digest"
    assert decision.quiet_hours_adjustment == True
