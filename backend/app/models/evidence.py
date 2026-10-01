from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class EvidenceRecord(Base):
    """
    Generalized evidence entity unifying Machine Health and Visual Inspection observations,
    inferences, and ground truth under a rigorous, typed schema.
    """
    __tablename__ = "evidence_records"

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

    domain: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # MACHINE_HEALTH | VISUAL_INSPECTION

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # MACHINE | INSPECTION_RUN | INSPECTION_RESULT | PREDICTION | RISK_ASSESSMENT | ALERT

    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Target entity identifier (e.g. machine UUID or turbofan unit ID, run UUID, result UUID)

    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # TELEMETRY | FEATURE | RUL_PREDICTION | HEALTH_INDEX | RISK_ASSESSMENT | RISK_REASON |
    # ALERT | IMAGE | ANOMALY_SCORE | INSPECTION_DECISION | LOCALIZATION | GROUND_TRUTH |
    # ANALYTICS | MODEL_ARTIFACT | DATASET_PROVENANCE

    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Originating engine/table (e.g. c_mapss_fd001, rul_model, risk_engine, mvtec_ad, patchcore)

    source_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    # Specific record or artifact URI (e.g. predictions:UUID, inspection_results:UUID)

    observation_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    observation_cycle: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    value: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # Typed payload (e.g. {"rul": 42.3}, {"anomaly_score": 3.42}, {"risk_state": "ELEVATED"})

    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # e.g. "cycles", "patch_distance", "ratio"

    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # NULL unless an authentic calibrated confidence score exists. NEVER fabricated.

    quality_state: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # VERIFIED | DERIVED | BENCHMARK_GROUND_TRUTH | PROVENANCE_ONLY | UNAVAILABLE

    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Deterministic factual explanation

    provenance: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    # Checksums, layer metadata, sampling hyperparameters

    model_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    feature_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    policy_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationships
    outgoing_relationships = relationship(
        "EvidenceRelationship",
        foreign_keys="EvidenceRelationship.source_evidence_id",
        back_populates="source_evidence",
        cascade="all, delete-orphan",
    )
    incoming_relationships = relationship(
        "EvidenceRelationship",
        foreign_keys="EvidenceRelationship.target_evidence_id",
        back_populates="target_evidence",
        cascade="all, delete-orphan",
    )
    bundle_items = relationship(
        "EvidenceBundleItem",
        back_populates="evidence",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_evidence_domain_entity", "domain", "entity_type", "entity_id"),
        Index("ix_evidence_type_source", "evidence_type", "source"),
    )


class EvidenceRelationship(Base):
    """
    Lightweight directed relationship between evidence records.
    Enforces domain isolation rules to prevent unsupported cross-domain fusion.
    """
    __tablename__ = "evidence_relationships"

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

    source_evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    target_evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # DERIVED_FROM | SUPPORTED_BY | PRODUCED_BY | EVALUATED_AGAINST | TRIGGERED | BELONGS_TO | HAS_ARTIFACT | HAS_PROVENANCE

    relationship_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    source_evidence = relationship("EvidenceRecord", foreign_keys=[source_evidence_id], back_populates="outgoing_relationships")
    target_evidence = relationship("EvidenceRecord", foreign_keys=[target_evidence_id], back_populates="incoming_relationships")

    __table_args__ = (
        Index("ix_evidence_rel_pair", "source_evidence_id", "target_evidence_id"),
    )


class EvidenceBundle(Base):
    """
    Group of related evidence items assembled for a cohesive investigative domain context.
    Strictly segregated by domain (MACHINE_HEALTH or VISUAL_INSPECTION).
    """
    __tablename__ = "evidence_bundles"

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

    bundle_name: Mapped[str] = mapped_column(String(100), nullable=False)
    domain: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    items = relationship(
        "EvidenceBundleItem",
        back_populates="bundle",
        cascade="all, delete-orphan",
        order_by="EvidenceBundleItem.display_order",
    )


class EvidenceBundleItem(Base):
    """
    Item membership within an EvidenceBundle.
    """
    __tablename__ = "evidence_bundle_items"

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

    bundle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_bundles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    role_in_bundle: Mapped[str] = mapped_column(String(50), nullable=False)
    # PRIMARY_OBSERVATION | MODEL_INFERENCE | RISK_ASSESSMENT | ALERT | ARTIFACT | GROUND_TRUTH | PROVENANCE

    bundle = relationship("EvidenceBundle", back_populates="items")
    evidence = relationship("EvidenceRecord", back_populates="bundle_items")

    __table_args__ = (
        Index("ix_bundle_evidence_unique", "bundle_id", "evidence_id", unique=True),
    )
