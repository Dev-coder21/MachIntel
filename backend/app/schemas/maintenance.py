from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class MaintenancePriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MaintenanceStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class MaintenanceSourceDomain(str, Enum):
    MACHINE_HEALTH = "MACHINE_HEALTH"
    VISUAL_INSPECTION = "VISUAL_INSPECTION"


class MaintenanceSourceType(str, Enum):
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    ALERT = "ALERT"
    INSPECTION_RESULT = "INSPECTION_RESULT"
    EVIDENCE_BUNDLE = "EVIDENCE_BUNDLE"


class MaintenanceEventType(str, Enum):
    CREATED = "CREATED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    COMMENT_ADDED = "COMMENT_ADDED"


class MaintenanceWorkOrderCreate(BaseModel):
    machine_id: Optional[str] = None
    source_domain: MaintenanceSourceDomain
    source_type: MaintenanceSourceType
    source_reference: str = Field(..., description="UUID or identifier of the source entity")
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[MaintenancePriority] = None
    recommended_action: Optional[str] = None
    reason: Optional[str] = None
    assigned_to_id: Optional[uuid.UUID] = None


class WorkOrderAcknowledgeRequest(BaseModel):
    assigned_to_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class WorkOrderStartRequest(BaseModel):
    notes: Optional[str] = None


class WorkOrderCompleteRequest(BaseModel):
    resolution_notes: str = Field(..., min_length=3, description="Detailed notes on the human-reviewed maintenance outcome")
    notes: Optional[str] = None


class WorkOrderCancelRequest(BaseModel):
    reason: str = Field(..., min_length=3, description="Justification for cancelling the maintenance item")
    notes: Optional[str] = None


class MaintenanceEventResponse(BaseModel):
    id: uuid.UUID
    work_order_id: uuid.UUID
    event_type: str
    from_status: Optional[str] = None
    to_status: str
    actor_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    event_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MaintenanceWorkOrderResponse(BaseModel):
    id: uuid.UUID
    machine_id: Optional[str] = None
    source_domain: str
    source_type: str
    source_reference: str
    deduplication_key: str
    title: str
    description: str
    priority: str
    status: str
    recommended_action: str
    reason: str
    risk_state_at_creation: Optional[str] = None
    predicted_rul_at_creation: Optional[float] = None
    health_index_at_creation: Optional[float] = None
    anomaly_score_at_creation: Optional[float] = None
    policy_version: str
    evidence_references: List[Dict[str, Any]] = Field(default_factory=list)
    created_by_id: Optional[uuid.UUID] = None
    assigned_to_id: Optional[uuid.UUID] = None
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    updated_at: datetime
    resolution_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MaintenanceWorkOrderDetailResponse(MaintenanceWorkOrderResponse):
    events: List[MaintenanceEventResponse] = Field(default_factory=list)
    source_entity_details: Optional[Dict[str, Any]] = None


class MaintenanceSummaryResponse(BaseModel):
    total_work_orders: int
    open_count: int
    acknowledged_count: int
    in_progress_count: int
    completed_count: int
    cancelled_count: int
    critical_priority_count: int
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int
    machine_health_count: int
    visual_inspection_count: int
    recent_activity: List[MaintenanceEventResponse] = Field(default_factory=list)
