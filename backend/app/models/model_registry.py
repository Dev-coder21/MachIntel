from datetime import datetime, timezone
import enum
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, TimestampMixin


class ModelDomain(str, enum.Enum):
    MACHINE_HEALTH = "MACHINE_HEALTH"
    VISUAL_INSPECTION = "VISUAL_INSPECTION"


class ModelLifecycleStatus(str, enum.Enum):
    REGISTERED = "REGISTERED"
    EVALUATED = "EVALUATED"
    CANDIDATE = "CANDIDATE"
    PROMOTED = "PROMOTED"
    RETIRED = "RETIRED"
    REJECTED = "REJECTED"


class EvaluationGateResult(str, enum.Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    INFORMATIONAL = "INFORMATIONAL"


class ModelRegistry(Base, TimestampMixin):
    """
    Authoritative model registry tracking prognostic & vision models,
    hyperparameters, validation/test metrics, reproducible manifests,
    cryptographic SHA-256 integrity, lifecycle states, and active deployment status.
    """
    __tablename__ = "model_registry"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    model_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    domain: Mapped[str] = mapped_column(String(50), default=ModelDomain.MACHINE_HEALTH.value, index=True, nullable=False)
    model_family: Mapped[str] = mapped_column(String(50), default="RUL_REGRESSION", index=True, nullable=False)
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)
    task: Mapped[str] = mapped_column(String(50), default="RUL_REGRESSION", nullable=False)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=ModelLifecycleStatus.REGISTERED.value, index=True, nullable=False)
    framework: Mapped[str] = mapped_column(String(50), default="scikit-learn", nullable=False)

    dataset_identifier: Mapped[str] = mapped_column(String(100), nullable=False)
    dataset_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    feature_engineering_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    feature_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    preprocessing_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    window_size: Mapped[int] = mapped_column(Integer, default=20, nullable=False)

    hyperparameters: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    feature_names: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    feature_importances: Mapped[Dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)

    artifact_path: Mapped[str] = mapped_column(String(500), nullable=False)
    artifact_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    artifact_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    training_manifest: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    evaluation_manifest: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    parent_model_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    predictions = relationship("Prediction", back_populates="model_version", cascade="all, delete-orphan")
    evaluations = relationship("ModelEvaluation", back_populates="model", cascade="all, delete-orphan", order_by="desc(ModelEvaluation.evaluated_at)")
    promotions = relationship("ModelPromotion", back_populates="model", cascade="all, delete-orphan", order_by="desc(ModelPromotion.promoted_at)")


class ModelEvaluation(Base):
    """
    Immutable evaluation record capturing deterministic gate results, test metrics,
    and reproducibility manifests for a specific registered model.
    """
    __tablename__ = "model_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_registry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evaluation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    dataset_identifier: Mapped[str] = mapped_column(String(100), nullable=False)
    split: Mapped[str] = mapped_column(String(50), nullable=False)
    metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    manifest: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    gate_result: Mapped[str] = mapped_column(String(50), default=EvaluationGateResult.PASSED.value, nullable=False)
    gate_details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    evaluator: Mapped[str] = mapped_column(String(100), default="automated-evaluator", nullable=False)

    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    model = relationship("ModelRegistry", back_populates="evaluations")


class ModelPromotion(Base):
    """
    Audit log of model promotion, demotion, and lifecycle transitions.
    """
    __tablename__ = "model_promotions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_registry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[str] = mapped_column(String(50), nullable=False)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    promoted_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    promotion_policy_version: Mapped[str] = mapped_column(String(50), default="policy-v1.0.0", nullable=False)
    gate_results: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    promoted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    model = relationship("ModelRegistry", back_populates="promotions")
    promoted_by = relationship("User")
