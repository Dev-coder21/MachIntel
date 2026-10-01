from datetime import datetime, timezone
import enum
from typing import Any, Dict, Optional
import uuid
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class JobType(str, enum.Enum):
    EVIDENCE_REFRESH = "EVIDENCE_REFRESH"
    RISK_REFRESH = "RISK_REFRESH"
    MAINTENANCE_RECOMMENDATION_REFRESH = "MAINTENANCE_RECOMMENDATION_REFRESH"
    ANALYTICS_REFRESH = "ANALYTICS_REFRESH"
    MODEL_INTEGRITY_CHECK = "MODEL_INTEGRITY_CHECK"


class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class BackgroundJob(Base):
    """
    Persistent record of a background operational task.
    Supports atomic locking, idempotency key deduplication, bounded retries,
    heartbeats, and execution summaries.
    """
    __tablename__ = "background_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), default=JobStatus.QUEUED.value, nullable=False, index=True
    )
    execution_key: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )

    requested_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    error_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    output_summary: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    retry_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    worker_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    heartbeat_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    requested_by = relationship("User", foreign_keys=[requested_by_id])


class WorkerHeartbeat(Base):
    """
    Live registry of active worker instances.
    Provides cluster-safe visibility into active processes, PIDs, hostnames,
    and current job processing status.
    """
    __tablename__ = "worker_heartbeats"

    worker_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    hostname: Mapped[str] = mapped_column(String(128), nullable=False)
    pid: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    current_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    metadata_info: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
