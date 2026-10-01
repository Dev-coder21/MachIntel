from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class RiskAssessment(Base):
    """
    Deterministic risk assessment derived from a machine's predicted RUL and Health Index.
    Encapsulates explainable reason codes, human-readable explanations, and evidence references.
    """
    __tablename__ = "risk_assessments"

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
    machine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("machines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prediction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("predictions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    risk_state: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    health_index: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_rul: Mapped[float] = mapped_column(Float, nullable=False)
    reason_codes: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_references: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    machine = relationship("Machine")
    prediction = relationship("Prediction")
    alerts = relationship("Alert", back_populates="risk_assessment", cascade="all, delete-orphan")
    transitions = relationship("RiskTransition", back_populates="risk_assessment", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_risk_assessments_machine_created", "machine_id", "created_at"),
    )


class RiskTransition(Base):
    """
    Records meaningful state transitions between consecutive analytical risk states for an asset.
    """
    __tablename__ = "risk_transitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    machine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("machines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    risk_assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("risk_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_state: Mapped[str] = mapped_column(String(30), nullable=False)
    to_state: Mapped[str] = mapped_column(String(30), nullable=False)
    observation_cycle: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    machine = relationship("Machine")
    risk_assessment = relationship("RiskAssessment", back_populates="transitions")

    __table_args__ = (
        Index("ix_risk_transitions_machine_time", "machine_id", "created_at"),
    )
