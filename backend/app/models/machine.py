import enum
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import Enum, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin


class MachineType(str, enum.Enum):
    TURBOFAN_ENGINE = "TURBOFAN_ENGINE"
    OPTICAL_INSPECTION_STATION = "OPTICAL_INSPECTION_STATION"
    ROTATING_ASSET = "ROTATING_ASSET"


class MachineStatus(str, enum.Enum):
    OPERATIONAL = "OPERATIONAL"
    MAINTENANCE = "MAINTENANCE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


class SplitCategory(str, enum.Enum):
    INTERNAL_TRAIN = "INTERNAL_TRAIN"   # Units 1-80
    INTERNAL_VAL = "INTERNAL_VAL"       # Units 81-100
    EVAL_TEST = "EVAL_TEST"             # Test units with RUL ground truth


class Machine(Base, TimestampMixin):
    __tablename__ = "machines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    machine_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    machine_type: Mapped[MachineType] = mapped_column(
        Enum(MachineType, name="machine_type", native_enum=False),
        default=MachineType.TURBOFAN_ENGINE,
        nullable=False,
    )
    source_dataset: Mapped[str] = mapped_column(String(100), nullable=False)
    source_entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    dataset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dataset_metadata.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[MachineStatus] = mapped_column(
        Enum(MachineStatus, name="machine_status", native_enum=False),
        default=MachineStatus.OPERATIONAL,
        nullable=False,
    )
    split_category: Mapped[SplitCategory] = mapped_column(
        Enum(SplitCategory, name="split_category", native_enum=False),
        default=SplitCategory.INTERNAL_TRAIN,
        nullable=False,
    )
    total_cycles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_cycle: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ground_truth_rul: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        UniqueConstraint("source_dataset", "source_entity_id", "split_category", name="uq_machine_source_entity"),
    )

    dataset = relationship("DatasetMetadata", back_populates="machines")
    telemetry_records = relationship(
        "TelemetryRecord",
        back_populates="machine",
        cascade="all, delete-orphan",
        order_by="TelemetryRecord.source_cycle",
    )
    data_quality_issues = relationship(
        "DataQualityIssue",
        back_populates="machine",
        cascade="all, delete-orphan",
    )
    predictions = relationship(
        "Prediction",
        back_populates="machine",
        cascade="all, delete-orphan",
    )
