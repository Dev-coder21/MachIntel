from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base


class OperationalState(str, Enum):
    NORMAL = "NORMAL"
    WATCH = "WATCH"
    ELEVATED = "ELEVATED"
    CRITICAL = "CRITICAL"


class Prediction(Base):
    """
    Persisted prognostic RUL inference record with strict provenance tracking.
    """
    __tablename__ = "predictions"

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
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_registry.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    dataset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_metadata.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    feature_engineering_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    observation_cycle: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    predicted_rul: Mapped[float] = mapped_column(Float, nullable=False)
    health_index: Mapped[float] = mapped_column(Float, nullable=False)
    operational_state: Mapped[str] = mapped_column(String(30), default="NORMAL", nullable=False, index=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    machine = relationship("Machine", back_populates="predictions")
    model_version = relationship("ModelRegistry", back_populates="predictions")
    dataset = relationship("DatasetMetadata")

    __table_args__ = (
        Index("ix_predictions_machine_cycle", "machine_id", "observation_cycle"),
    )
