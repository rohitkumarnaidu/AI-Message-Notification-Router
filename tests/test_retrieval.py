import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "code"))

from retriever import retrieve_evidence
from schemas import IncomingMessageContext

def test_retrieval_temporal_leakage():
    msg_ctx = IncomingMessageContext(
        message_id="msg_001",
        original_index=0,
        timestamp="2026-07-31 10:00",
        conversation_type="personal",
        text="Hello",
        media_type="",
        media_id="",
        user_context={"user_id": "u_001"},
        sender_context={"user_id": "u_002"}
    )
    full_ctx = {
        "message_history": [
            {"message_id": "message_0001", "user_id": "u_001", "sender_user_id": "u_002", "created_at": "2026-07-31 09:00", "message_text": "Hi", "conversation_type": "personal"}, # valid
            {"message_id": "message_0002", "user_id": "u_001", "sender_user_id": "u_002", "created_at": "2026-07-31 11:00", "message_text": "Future", "conversation_type": "personal"} # future leakage
        ],
        "message_events": [
            {"message_id": "message_0001", "message_replied": "1"}
        ]
    }
    
    ev = retrieve_evidence(msg_ctx, full_ctx)
    assert len(ev) == 1
    assert ev[0].message_id == "message_0001"


def test_retrieval_user_isolation():
    msg_ctx = IncomingMessageContext(
        message_id="msg_002",
        original_index=1,
        timestamp="2026-07-31 10:00",
        conversation_type="personal",
        text="Hello",
        media_type="",
        media_id="",
        user_context={"user_id": "u_001"},
        sender_context={"user_id": "u_002"}
    )
    full_ctx = {
        "message_history": [
            {"message_id": "message_0003", "user_id": "u_003", "sender_user_id": "u_002", "created_at": "2026-07-31 09:00", "message_text": "Hi", "conversation_type": "personal"}, # different user
        ],
        "message_events": []
    }
    
    ev = retrieve_evidence(msg_ctx, full_ctx)
    assert len(ev) == 0


def test_retrieval_minimum_threshold():
    msg_ctx = IncomingMessageContext(
        message_id="msg_003",
        original_index=2,
        timestamp="2026-07-31 10:00",
        conversation_type="personal",
        text="Hello",
        media_type="",
        media_id="",
        user_context={"user_id": "u_001"},
        sender_context={"user_id": "u_002"}
    )
    full_ctx = {
        "message_history": [
            {"message_id": "message_0004", "user_id": "u_001", "sender_user_id": "u_999", "created_at": "2026-07-31 09:00", "message_text": "Random text with no overlap", "conversation_type": "group"} # low score
        ],
        "message_events": []
    }
    
    ev = retrieve_evidence(msg_ctx, full_ctx)
    assert len(ev) == 0

def test_prediction_id_leakage():
    msg_ctx = IncomingMessageContext(
        message_id="msg_004",
        original_index=3,
        timestamp="2026-07-31 10:00",
        conversation_type="personal",
        text="Hello",
        media_type="",
        media_id="",
        user_context={"user_id": "u_001"},
        sender_context={"user_id": "u_002"}
    )
    full_ctx = {
        "message_history": [
            {"message_id": "msg_000", "user_id": "u_001", "sender_user_id": "u_002", "created_at": "2026-07-31 09:00", "message_text": "Hi", "conversation_type": "personal"}, # prediction ID
        ],
        "message_events": []
    }
    
    ev = retrieve_evidence(msg_ctx, full_ctx)
    assert len(ev) == 0
