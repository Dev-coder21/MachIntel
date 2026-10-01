from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class EvidenceDomain(str, Enum):
    MACHINE_HEALTH = "MACHINE_HEALTH"
    VISUAL_INSPECTION = "VISUAL_INSPECTION"


class EvidenceEntityType(str, Enum):
    MACHINE = "MACHINE"
    INSPECTION_RUN = "INSPECTION_RUN"
    INSPECTION_RESULT = "INSPECTION_RESULT"
    PREDICTION = "PREDICTION"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    ALERT = "ALERT"


class EvidenceType(str, Enum):
    TELEMETRY = "TELEMETRY"
    FEATURE = "FEATURE"
    RUL_PREDICTION = "RUL_PREDICTION"
    HEALTH_INDEX = "HEALTH_INDEX"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    RISK_REASON = "RISK_REASON"
    ALERT = "ALERT"
    IMAGE = "IMAGE"
    ANOMALY_SCORE = "ANOMALY_SCORE"
    INSPECTION_DECISION = "INSPECTION_DECISION"
    LOCALIZATION = "LOCALIZATION"
    GROUND_TRUTH = "GROUND_TRUTH"
    ANALYTICS = "ANALYTICS"
    MODEL_ARTIFACT = "MODEL_ARTIFACT"
    DATASET_PROVENANCE = "DATASET_PROVENANCE"


class EvidenceQualityState(str, Enum):
    VERIFIED = "VERIFIED"
    DERIVED = "DERIVED"
    BENCHMARK_GROUND_TRUTH = "BENCHMARK_GROUND_TRUTH"
    PROVENANCE_ONLY = "PROVENANCE_ONLY"
    UNAVAILABLE = "UNAVAILABLE"


class EvidenceRelationshipType(str, Enum):
    DERIVED_FROM = "DERIVED_FROM"
    SUPPORTED_BY = "SUPPORTED_BY"
    PRODUCED_BY = "PRODUCED_BY"
    EVALUATED_AGAINST = "EVALUATED_AGAINST"
    TRIGGERED = "TRIGGERED"
    BELONGS_TO = "BELONGS_TO"
    HAS_ARTIFACT = "HAS_ARTIFACT"
    HAS_PROVENANCE = "HAS_PROVENANCE"


class EvidenceObject(BaseModel):
    """M5 EvidenceObject schema maintained for prognostic risk reference compatibility."""
    model_config = ConfigDict(from_attributes=True)

    machine_id: str
    evidence_type: str
    source: str
    source_reference: str
    observation_cycle: Optional[int] = None
    observed_at: Optional[datetime] = None
    value: Any = None
    unit: Optional[str] = None
    confidence: Optional[float] = None
    provenance: Dict[str, Any] = Field(default_factory=dict)
    model_version: Optional[str] = None
    feature_version: Optional[str] = None


class EvidenceRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    domain: str
    entity_type: str
    entity_id: str
    evidence_type: str
    source: str
    source_reference: str
    observation_time: Optional[datetime] = None
    observation_cycle: Optional[int] = None
    value: Optional[Dict[str, Any]] = None
    unit: Optional[str] = None
    confidence: Optional[float] = None
    quality_state: str
    explanation: Optional[str] = None
    provenance: Dict[str, Any] = Field(default_factory=dict)
    model_version: Optional[str] = None
    feature_version: Optional[str] = None
    policy_version: Optional[str] = None
    created_at: datetime


class EvidenceRelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_evidence_id: uuid.UUID
    target_evidence_id: uuid.UUID
    relationship_type: str
    relationship_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    source_evidence: Optional[EvidenceRecordResponse] = None
    target_evidence: Optional[EvidenceRecordResponse] = None


class EvidenceBundleItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bundle_id: uuid.UUID
    evidence_id: uuid.UUID
    display_order: int
    role_in_bundle: str
    evidence: Optional[EvidenceRecordResponse] = None


class EvidenceBundleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    bundle_name: str
    domain: str
    entity_type: str
    entity_id: str
    description: Optional[str] = None
    items: List[EvidenceBundleItemResponse] = Field(default_factory=list)
    created_at: datetime


class EvidenceTimelineItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    domain: str
    entity_type: str
    entity_id: str
    evidence_type: str
    source: str
    observation_cycle: Optional[int] = None
    observation_time: Optional[datetime] = None
    value: Optional[Dict[str, Any]] = None
    quality_state: str
    explanation: Optional[str] = None
    created_at: datetime


class EvidenceProvenanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_id: uuid.UUID
    domain: str
    entity_type: str
    entity_id: str
    evidence_type: str
    source: str
    source_reference: str
    provenance: Dict[str, Any] = Field(default_factory=dict)
    model_version: Optional[str] = None
    feature_version: Optional[str] = None
    policy_version: Optional[str] = None
    quality_state: str
    created_at: datetime


class EvidenceSearchResponse(BaseModel):
    total: int
    records: List[EvidenceRecordResponse]
    domain: Optional[str] = None
