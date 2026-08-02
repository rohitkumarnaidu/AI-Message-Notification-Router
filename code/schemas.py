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
    # Provider tracking
    provider: str = ""
    model: str = ""
    operation: str = ""
    attempts: int = 0
    latency: float = 0.0
    success: bool = False
    failure_category: Optional[str] = None

@dataclass
class ImageAnalysis(MediaAnalysis):
    ocr_text: str = ""
    visual_summary: str = ""
    has_qr_code: bool = False
    has_financial_elements: bool = False
    has_promotional_elements: bool = False
    is_prompt_injection: bool = False

@dataclass
class VoiceAnalysis(MediaAnalysis):
    transcript: str = ""
    detected_language: str = ""
    has_financial_elements: bool = False
    has_promotional_elements: bool = False
    is_prompt_injection: bool = False
    contains_otp_request: bool = False
    contains_credential_request: bool = False
    contains_urgent_language: bool = False

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
class RouterDecision:
    action: str
    message_type: str
    reason: str
    confidence: float
    evidence_message_ids: List[str]
    decision_signals: List[str] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)
    # Provider tracking
    provider: str = ""
    model: str = ""
    operation: str = ""
    attempts: int = 0
    latency: float = 0.0
    success: bool = False
    failure_category: Optional[str] = None
    structured_output_status: str = ""

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


# ============================================================
# PHASE 12: SAFETY SCHEMA — FROZEN SHARED INTERFACES
# ============================================================

from enum import Enum


class RiskCategory(str, Enum):
    """Canonical risk categories. Each must have entry/exit conditions and tests."""
    NONE = "NONE"
    LOW_VALUE = "LOW_VALUE"
    SPAM = "SPAM"
    PROMOTION_UNWANTED = "PROMOTION_UNWANTED"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    CREDENTIAL_RISK = "CREDENTIAL_RISK"
    PAYMENT_RISK = "PAYMENT_RISK"
    IMPERSONATION_RISK = "IMPERSONATION_RISK"
    PHISHING_RISK = "PHISHING_RISK"
    DANGEROUS_FORWARD = "DANGEROUS_FORWARD"
    UNKNOWN_HIGH_RISK = "UNKNOWN_HIGH_RISK"


# Risk tier mapping (higher = more restrictive)
RISK_TIER_MAP = {
    RiskCategory.NONE: 0,
    RiskCategory.LOW_VALUE: 1,
    RiskCategory.SPAM: 2,
    RiskCategory.PROMOTION_UNWANTED: 2,
    RiskCategory.DANGEROUS_FORWARD: 3,
    RiskCategory.PROMPT_INJECTION: 4,
    RiskCategory.UNKNOWN_HIGH_RISK: 4,
    RiskCategory.IMPERSONATION_RISK: 5,
    RiskCategory.PAYMENT_RISK: 6,
    RiskCategory.PHISHING_RISK: 7,
    RiskCategory.CREDENTIAL_RISK: 8,
}


@dataclass
class SignalSource:
    """Records where a safety signal was extracted from."""
    source: str          # text | image_ocr | image_visual | voice_transcript | sender_meta | business_meta | group_ctx | history | link_parser | temporal
    grounded_value: str  # the exact content fragment that triggered this signal
    detector: str        # detector module and rule name
    confidence: float    # 0.0-1.0 signal confidence
    trusted: bool        # whether the source is considered trusted
    timestamp: str = ""  # when relevant (evidence timestamps)


@dataclass
class SafetySignals:
    """
    Canonical safety signals for Phase 12.
    All fields include source provenance via SignalSource.
    Deterministic policy owns final safety constraints — model output cannot override.
    """
    # --- Credential risk signals ---
    credential_request: bool = False
    otp_request: bool = False
    password_request: bool = False
    pin_request: bool = False
    credential_warning: bool = False   # "never share your OTP" — NOT a risk
    credential_sources: List[SignalSource] = field(default_factory=list)

    # --- Payment risk signals ---
    payment_request: bool = False
    payment_destination_trust: str = "unknown"  # trusted | unknown | suspicious
    suspicious_link: bool = False
    domain_trust: str = "unknown"       # trusted | unknown | suspicious | shortener
    qr_present: bool = False
    qr_decoded: Optional[str] = None    # decoded QR content if available
    payment_sources: List[SignalSource] = field(default_factory=list)

    # --- Account/social pressure signals ---
    account_blocking_pressure: bool = False
    reward_or_lottery: bool = False
    impersonation_signal: bool = False
    dangerous_forward_signal: bool = False
    pressure_sources: List[SignalSource] = field(default_factory=list)

    # --- Content signals ---
    promotion_signal: bool = False
    prompt_injection_signal: bool = False
    injection_sources: List[SignalSource] = field(default_factory=list)

    # --- Urgency signals ---
    urgency_language: bool = False
    concrete_deadline: bool = False     # specific time/date mentioned
    urgency_sources: List[SignalSource] = field(default_factory=list)

    # --- Relationship/context signals ---
    legitimate_relationship: bool = False
    business_relationship: bool = False
    trusted_sender_context: bool = False
    historical_report_signal: bool = False
    historical_engagement_signal: bool = False

    # --- Media quality ---
    media_grounding_quality: str = "none"  # none | failed | low | medium | high

    # --- Evidence quality ---
    evidence_quality: str = "none"  # none | cross_user | future | weak | moderate | strong

    # --- Conflict and uncertainty ---
    conflicting_signals: List[str] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)

    # --- Risk assessment ---
    risk_score: float = 0.0            # 0.0-1.0, computed from signal combination
    risk_tier: int = 0                 # 0-8, from RISK_TIER_MAP
    risk_category: str = "NONE"        # primary RiskCategory value
    recommended_constraint: str = "none"  # none | digest | mute | mute_scam

    # --- Metadata ---
    detector_version: str = "phase12_v1"
    multilingual_normalized: bool = False
    detected_language: str = "unknown"


@dataclass
class PolicyDecision:
    """
    Output of the deterministic policy resolver.
    This owns the final safety constraints — model proposal is subordinate.
    """
    final_action: str
    final_message_type: str
    override_applied: bool = False
    override_reason_code: str = ""       # internal trace code
    confidence_ceiling: float = 0.99     # max confidence allowed
    confidence_floor: float = 0.0
    required_reason_signals: List[str] = field(default_factory=list)
    allowed_evidence_ids: List[str] = field(default_factory=list)
    trace: List[str] = field(default_factory=list)
    safety_signals: Optional['SafetySignals'] = None


@dataclass
class ExecutionTrace:
    """Single override log entry for audit trail."""
    step: int
    rule: str
    original_action: str
    original_type: str
    new_action: str
    new_type: str
    reason: str
    confidence_delta: float = 0.0


@dataclass
class UnsafeNotifyResult:
    """Result of the unsafe-notify validator."""
    proposed_action: str
    blocking_condition: str        # "" if not blocked
    final_action: str
    policy_version: str = "phase12_v1"
    confidence_adjustment: float = 0.0
    reason_adjustment: str = ""
    blocked: bool = False

# ============================================================
# PHASE 13: INTERRUPTION POLICY SCHEMA — FROZEN SHARED INTERFACES
# ============================================================

@dataclass
class TemporalContext:
    message_timestamp: str = ""
    normalized_timezone: str = "UTC"
    local_datetime: Optional[str] = None
    day_of_week: str = ""
    is_quiet_hours: bool = False
    quiet_hours_source: str = ""
    deadline_timestamp: Optional[str] = None
    deadline_status: str = "none" # none | future | expired
    time_until_deadline: Optional[float] = None
    event_timestamp: Optional[str] = None
    event_status: str = "none"
    temporal_phrases: List[str] = field(default_factory=list)
    temporal_uncertainties: List[str] = field(default_factory=list)

@dataclass
class RelevanceSignals:
    direct_message: bool = False
    direct_mention: bool = False
    active_relationship: bool = False
    recent_engagement: bool = False
    current_transaction: bool = False
    current_delivery: bool = False
    user_opt_in: bool = False
    user_opt_out: bool = False
    personal_request: bool = False
    required_response: bool = False
    consequence_of_delay: str = "none"

@dataclass
class InterruptionSignals:
    genuine_urgency: bool = False
    urgency_language_only: bool = False
    immediate_action_required: bool = False
    deadline_strength: float = 0.0
    user_consequence: float = 0.0
    personal_relevance: float = 0.0
    safety_risk: float = 0.0
    quiet_hours: bool = False
    notification_load: str = "normal" # low | normal | high
    group_muted: bool = False
    direct_mention: bool = False
    group_admin: bool = False
    duplicate_or_repeated: bool = False
    promotion: bool = False
    low_value: bool = False

@dataclass
class InterruptionDecision:
    proposed_action: str = ""
    final_action: str = ""
    message_type: str = ""
    policy_override: bool = False
    override_reason: str = ""
    urgency_score: float = 0.0
    relevance_score: float = 0.0
    interruption_cost: float = 0.0
    safety_constraint: Optional[str] = None
    quiet_hours_adjustment: bool = False
    notification_load_adjustment: bool = False
    group_adjustment: bool = False
    confidence_constraints: List[float] = field(default_factory=list)
