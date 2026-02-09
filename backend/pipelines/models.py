"""Pydantic models for the Slack digest system."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from enum import Enum

class DecisionType(str, Enum):
    REQUIREMENT_CHANGE = "requirement_change"
    DESIGN_DECISION = "design_decision"
    APPROVAL = "approval"

class RelationshipType(str, Enum):
    IMPACTS = "IMPACTS"
    REFERENCES = "REFERENCES"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    DEPENDS_ON = "DEPENDS_ON"

class EmbeddingStatus(str, Enum):
    PENDING = "pending"
    EMBEDDED = "embedded"
    FAILED = "failed"

class UserProfile(BaseModel):
    user_id: str
    user_name: str
    role: str
    owned_components: List[str] = []
    email: str

class SlackMessage(BaseModel):
    message_id: str
    channel_id: str
    thread_id: Optional[str] = None
    user_id: str
    message_text: str
    timestamp: datetime
    entities: Dict[str, Any] = {}

class Decision(BaseModel):
    decision_id: Optional[int] = None
    thread_id: str
    timestamp: datetime
    author_user_id: str
    decision_type: DecisionType
    decision_text: str
    affected_components: List[str] = []
    referenced_reqs: List[str] = []
    embedding_status: EmbeddingStatus = EmbeddingStatus.PENDING

class DecisionDetail(BaseModel):
    decision_id: int
    detail_name: str
    detail_value: Dict[str, Any]

class DecisionRelationship(BaseModel):
    source_decision_id: int
    target_decision_id: int
    relationship_type: RelationshipType
    confidence: float = 0.0

class ExtractedEntities(BaseModel):
    requirements: List[str] = []
    components: List[str] = []
    decision_indicators: List[str] = []
    before_after_changes: List[Dict[str, str]] = []
    decision_type: Optional[DecisionType] = None

class DigestEntry(BaseModel):
    decision_id: int
    title: str
    summary: str
    impact_summary: str
    before_after: Optional[Dict[str, str]] = None
    affected_components: List[str]
    citations: List[str]
    timestamp: datetime

class PersonalizedDigest(BaseModel):
    user_id: str
    date: datetime
    summary: str
    themes: List[str]
    entries: List[DigestEntry]
    gaps_detected: List[str] = []
    action_items: List[str] = []