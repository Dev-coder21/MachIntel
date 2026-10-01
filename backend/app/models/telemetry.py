from datetime import datetime, timezone
from typing import Optional
import uuid
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base


class TelemetryRecord(Base):
    """
    Individual operational telemetry cycle measurement from industrial assets.
    Sensor channels and operational settings are persisted as first-class numeric columns.
    """
    __tablename__ = "telemetry_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    machine_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("machines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_cycle: Mapped[int] = mapped_column(Integer, nullable=False)
    event_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Authoritative wall-clock event time if available. NULL for discrete-cycle simulations.",
    )
    split_type: Mapped[str] = mapped_column(String(20), default="TRAIN", nullable=False)

    # Operational Settings
    op_setting_1: Mapped[float] = mapped_column(Float, nullable=False)
    op_setting_2: Mapped[float] = mapped_column(Float, nullable=False)
    op_setting_3: Mapped[float] = mapped_column(Float, nullable=False)

    # Sensor Channels 1-21
    sensor_1: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_2: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_3: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_4: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_5: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_6: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_7: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_8: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_9: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_10: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_11: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_12: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_13: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_14: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_15: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_16: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_17: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_18: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_19: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_20: Mapped[float] = mapped_column(Float, nullable=False)
    sensor_21: Mapped[float] = mapped_column(Float, nullable=False)

    ingestion_batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("machine_id", "source_cycle", "split_type", name="uq_telemetry_machine_cycle_split"),
        Index("ix_telemetry_machine_cycle", "machine_id", "source_cycle"),
    )

    machine = relationship("Machine", back_populates="telemetry_records")
