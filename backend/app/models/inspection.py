from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class InspectionRun(Base):
    """
    Persisted visual inspection run representing an evaluated batch or model benchmark.
    Tracks model, feature pipeline, decision policy, and aggregate evaluation metrics.
    """
    __tablename__ = "inspection_runs"

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

    dataset_identifier: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="metal_nut")
    model_version: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    feature_config_version: Mapped[str] = mapped_column(String(50), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="COMPLETED")
    threshold: Mapped[float] = mapped_column(Float, nullable=False)

    total_images: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    defect_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    evaluation_summary: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    results = relationship("InspectionResult", back_populates="run", cascade="all, delete-orphan")


class InspectionResult(Base):
    """
    Individual image-level inspection result with deterministic anomaly score,
    PASS/DEFECT decision, heatmap reference, and ground truth evaluation metadata.
    """
    __tablename__ = "inspection_results"

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

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inspection_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    split: Mapped[str] = mapped_column(String(20), nullable=False, default="test")
    defect_class: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    source_image_filename: Mapped[str] = mapped_column(String(100), nullable=False)

    image_level_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # "PASS" or "DEFECT"
    ground_truth_label: Mapped[str] = mapped_column(String(20), nullable=False)    # "PASS" or "DEFECT"

    heatmap_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    overlay_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ground_truth_mask_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    inference_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    run = relationship("InspectionRun", back_populates="results")

    __table_args__ = (
        Index("ix_inspection_results_run_decision", "run_id", "decision"),
        Index("ix_inspection_results_run_defect_class", "run_id", "defect_class"),
    )
