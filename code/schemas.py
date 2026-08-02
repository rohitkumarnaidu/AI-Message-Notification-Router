"""
Schema definitions and constants for the Message Notification Router dataset and deliverables.
Architecture-neutral constants for input dataset and output contract validation.
"""

# Required columns for dataset/messages.csv
MESSAGES_CSV_COLUMNS = (
    "message_id",
    "user_id",
    "conversation_type",
    "group_id",
    "business_id",
    "sender_user_id",
    "created_at",
    "message_text",
    "media_type",
    "media_id",
    "forwarded_count",
)

# Required columns for dataset/output.csv (and any valid submission output)
OUTPUT_CSV_COLUMNS = (
    "message_id",
    "action",
    "message_type",
    "reason",
    "confidence",
    "evidence_message_ids",
)

# Allowed actions in output contract
ALLOWED_ACTIONS = {"notify", "digest", "mute"}

# Allowed message types in output contract (per problem_statement.md lines 100-110)
ALLOWED_MESSAGE_TYPES = {
    "personal",
    "urgent",
    "event",
    "payment",
    "business_update",
    "promotion",
    "greeting",
    "forward",
    "spam",
    "scam",
    "unknown",
}

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class IncomingMessageContext:
    message_id: str
    original_index: int
    timestamp: str
    conversation_type: str
    text: str
    media_type: str
    media_id: str
    user_context: Dict[str, Any] = field(default_factory=dict)
    sender_context: Dict[str, Any] = field(default_factory=dict)
    group_context: Dict[str, Any] = field(default_factory=dict)
    business_context: Dict[str, Any] = field(default_factory=dict)
    historical_context: Dict[str, Any] = field(default_factory=dict)
    media_analysis: Optional['MediaAnalysis'] = None
    deterministic_signals: Dict[str, Any] = field(default_factory=dict)
    missing_context: List[str] = field(default_factory=list)

@dataclass
class UserProfile:
    user_id: str
    quiet_hours: str
    notification_load: float
    trusted_senders: List[str]
    active_groups: List[str]
    muted_groups: List[str]
    business_opt_ins: List[str]
    business_opt_outs: List[str]
    recent_transactions: List[str]
    reply_patterns: float
    dismiss_patterns: float
    report_patterns: float
    history_strength: str

@dataclass
class MediaAnalysis:
    media_id: str
    media_type: str
    extracted_text: str
    summary: str
    language: str
    urgency_signals: List[str]
    risk_signals: List[str]
    promotion_signals: List[str]
    event_signals: List[str]
    quality: str
    confidence: float
    failure: bool
    failure_reason: str
    processor_version: str

@dataclass
class EvidenceCandidate:
    message_id: str
    relationship_type: str
    behavioral_signal: str
    timestamp: str
    lexical_score: float
    semantic_score: float
    recency_score: float
    eligibility: bool
    exclusion_reason: str

@dataclass
class RouterDecision:
    action: str
    message_type: str
    reason: str
    confidence: float
    evidence_message_ids: List[str]
    decision_signals: List[str] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)

@dataclass
class FinalDecision:
    message_id: str
    original_index: int
    action: str
    message_type: str
    reason: str
    confidence: float
    evidence_message_ids: List[str]
    policy_overrides: List[str] = field(default_factory=list)
    validation_status: str = 'valid'
