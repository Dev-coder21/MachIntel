from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import DateTime, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin


class DatasetMetadata(Base, TimestampMixin):
    """
    Formal dataset provenance record preserving authoritative dataset origin,
    checksums, versions, and validation profiles.
    """
    __tablename__ = "dataset_metadata"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    dataset_name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    dataset_identifier: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    license: Mapped[str] = mapped_column(String(100), nullable=False)
    retrieval_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    file_checksums: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    preprocessing_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    ingestion_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    active_sensors: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    invariant_sensors: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    machines = relationship("Machine", back_populates="dataset")
    data_quality_issues = relationship("DataQualityIssue", back_populates="dataset")
