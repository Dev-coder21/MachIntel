from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import DateTime, Float, ForeignKey, Index, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


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


class MaintenanceWorkOrder(Base):
    """
    Structured Maintenance Work Order representing a human-reviewed maintenance task
    grounded in authentic operational evidence (RiskAssessment, Alert, InspectionResult, or EvidenceBundle).
    Strictly decision-support: does not issue direct machinery/actuator commands.
    """
    __tablename__ = "maintenance_work_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    def __init__(self, **kwargs):
        if "id" not in kwargs or kwargs["id"] is None:
            kwargs["id"] = uuid.uuid4()
        super().__init__(**kwargs)

    # Asset linkage: machine_id is populated for MACHINE_HEALTH items; nullable for VISUAL_INSPECTION items
    machine_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    # Domain separation (strictly MACHINE_HEALTH or VISUAL_INSPECTION)
    source_domain: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # Source entity reference
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    source_reference: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # Deterministic deduplication key: e.g. "RISK_ASSESSMENT:{risk_id}:maintenance-policy-v1.0.0"
    deduplication_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # Work Order Description & Guidance
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=MaintenancePriority.MEDIUM.value,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=MaintenanceStatus.OPEN.value,
        index=True,
    )
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    # Evidence Context Snapshot at Creation
    risk_state_at_creation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    predicted_rul_at_creation: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    health_index_at_creation: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    anomaly_score_at_creation: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False, default="maintenance-policy-v1.0.0")

    # Traceable evidence references
    evidence_references: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    # User Roles & Attribution
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Lifecycle Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Outcome & Resolution
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    events = relationship("MaintenanceEvent", back_populates="work_order", cascade="all, delete-orphan", order_by="MaintenanceEvent.created_at.asc()")

    __table_args__ = (
        Index("ix_maintenance_domain_status", "source_domain", "status"),
        Index("ix_maintenance_machine_status", "machine_id", "status"),
    )


class MaintenanceEvent(Base):
    """
    Immutable audit event tracking lifecycle transitions and human operator updates
    for a MaintenanceWorkOrder.
    """
    __tablename__ = "maintenance_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    def __init__(self, **kwargs):
        if "id" not in kwargs or kwargs["id"] is None:
            kwargs["id"] = uuid.uuid4()
        super().__init__(**kwargs)

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("maintenance_work_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # CREATED | ACKNOWLEDGED | STARTED | COMPLETED | CANCELLED | COMMENT_ADDED

    from_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)

    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    work_order = relationship("MaintenanceWorkOrder", back_populates="events")
    actor = relationship("User", foreign_keys=[actor_id])
