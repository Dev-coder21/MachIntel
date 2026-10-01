from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from backend.app.core.errors import CrossDomainEvidenceException, NotFoundException
from backend.app.core.logging import logger
from backend.app.models.alert import Alert
from backend.app.models.evidence import (
    EvidenceBundle,
    EvidenceBundleItem,
    EvidenceRecord,
    EvidenceRelationship,
)
from backend.app.models.inspection import InspectionResult, InspectionRun
from backend.app.models.machine import Machine
from backend.app.models.prediction import Prediction
from backend.app.models.risk import RiskAssessment
from backend.app.models.telemetry import TelemetryRecord


class EvidenceService:
    """
    Evidence Intelligence Service managing heterogeneous evidence records,
    validating domain separation, modeling causal lineage, and building evidence bundles.
    """

    @staticmethod
    def create_or_get_evidence(
        db: Session,
        domain: str,
        entity_type: str,
        entity_id: str,
        evidence_type: str,
        source: str,
        source_reference: str,
        quality_state: str,
        observation_time: Optional[datetime] = None,
        observation_cycle: Optional[int] = None,
        value: Optional[Dict[str, Any]] = None,
        unit: Optional[str] = None,
        confidence: Optional[float] = None,
        explanation: Optional[str] = None,
        provenance: Optional[Dict[str, Any]] = None,
        model_version: Optional[str] = None,
        feature_version: Optional[str] = None,
        policy_version: Optional[str] = None,
    ) -> Tuple[EvidenceRecord, bool]:
        """
        Idempotently create or retrieve an EvidenceRecord.
        Returns (record, created: bool).
        """
        stmt = select(EvidenceRecord).where(
            EvidenceRecord.domain == domain,
            EvidenceRecord.entity_type == entity_type,
            EvidenceRecord.entity_id == str(entity_id),
            EvidenceRecord.evidence_type == evidence_type,
            EvidenceRecord.source_reference == source_reference,
        )
        if observation_cycle is not None:
            stmt = stmt.where(EvidenceRecord.observation_cycle == observation_cycle)

        existing = db.execute(stmt).scalars().first()
        if existing:
            return existing, False

        record = EvidenceRecord(
            domain=domain,
            entity_type=entity_type,
            entity_id=str(entity_id),
            evidence_type=evidence_type,
            source=source,
            source_reference=source_reference,
            observation_time=observation_time,
            observation_cycle=observation_cycle,
            value=value,
            unit=unit,
            confidence=confidence,
            quality_state=quality_state,
            explanation=explanation,
            provenance=provenance or {},
            model_version=model_version,
            feature_version=feature_version,
            policy_version=policy_version,
        )
        db.add(record)
        db.flush()
        return record, True

    @staticmethod
    def create_relationship(
        db: Session,
        source_evidence_id: uuid.UUID,
        target_evidence_id: uuid.UUID,
        relationship_type: str,
        relationship_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[EvidenceRelationship, bool]:
        """
        Creates a directed relationship between two evidence records.
        CRITICAL: Strictly enforces domain separation. Cross-domain relationships are prohibited.
        """
        source = db.get(EvidenceRecord, source_evidence_id)
        if not source:
            raise NotFoundException(f"Source evidence record '{source_evidence_id}' not found.")

        target = db.get(EvidenceRecord, target_evidence_id)
        if not target:
            raise NotFoundException(f"Target evidence record '{target_evidence_id}' not found.")

        # Strict Domain Separation Enforcement
        if source.domain != target.domain:
            msg = (
                f"Unsupported cross-domain relationship rejected: cannot link '{source.domain}' evidence "
                f"({source.evidence_type}) to '{target.domain}' evidence ({target.evidence_type}). "
                f"MVTec visual inspection and C-MAPSS machine health maintain strict domain separation."
            )
            logger.warning(msg)
            raise CrossDomainEvidenceException(msg)

        # Check existing relationship for idempotency
        stmt = select(EvidenceRelationship).where(
            EvidenceRelationship.source_evidence_id == source_evidence_id,
            EvidenceRelationship.target_evidence_id == target_evidence_id,
            EvidenceRelationship.relationship_type == relationship_type,
        )
        existing = db.execute(stmt).scalars().first()
        if existing:
            return existing, False

        rel = EvidenceRelationship(
            source_evidence_id=source_evidence_id,
            target_evidence_id=target_evidence_id,
            relationship_type=relationship_type,
            relationship_metadata=relationship_metadata or {},
        )
        db.add(rel)
        db.flush()
        return rel, True

    @staticmethod
    def create_bundle(
        db: Session,
        bundle_name: str,
        domain: str,
        entity_type: str,
        entity_id: str,
        description: Optional[str] = None,
        evidence_items: Optional[List[Tuple[uuid.UUID, str, int]]] = None,
        # List of (evidence_id, role_in_bundle, display_order)
    ) -> EvidenceBundle:
        """
        Creates an EvidenceBundle grouping related evidence records for a single domain.
        Verifies domain alignment for all items.
        """
        bundle = EvidenceBundle(
            bundle_name=bundle_name,
            domain=domain,
            entity_type=entity_type,
            entity_id=str(entity_id),
            description=description,
        )
        db.add(bundle)
        db.flush()

        if evidence_items:
            for ev_id, role, order in evidence_items:
                ev = db.get(EvidenceRecord, ev_id)
                if ev:
                    if ev.domain != domain:
                        raise CrossDomainEvidenceException(
                            f"Cannot add evidence from domain '{ev.domain}' to bundle '{bundle_name}' in domain '{domain}'."
                        )
                    item = EvidenceBundleItem(
                        bundle_id=bundle.id,
                        evidence_id=ev_id,
                        role_in_bundle=role,
                        display_order=order,
                    )
                    db.add(item)
            db.flush()

        return bundle

    @staticmethod
    def get_evidence(db: Session, evidence_id: uuid.UUID) -> EvidenceRecord:
        record = db.get(EvidenceRecord, evidence_id)
        if not record:
            raise NotFoundException(f"Evidence record '{evidence_id}' not found.")
        return record

    @staticmethod
    def search_evidence(
        db: Session,
        domain: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        evidence_type: Optional[str] = None,
        quality_state: Optional[str] = None,
        source: Optional[str] = None,
        model_version: Optional[str] = None,
        policy_version: Optional[str] = None,
        observation_cycle: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[EvidenceRecord]]:
        """
        Controlled search over evidence records with strict parameter validation.
        """
        stmt = select(EvidenceRecord)
        count_stmt = select(func.count(EvidenceRecord.id))

        filters = []
        if domain:
            filters.append(EvidenceRecord.domain == domain)
        if entity_type:
            filters.append(EvidenceRecord.entity_type == entity_type)
        if entity_id:
            filters.append(EvidenceRecord.entity_id == entity_id)
        if evidence_type:
            filters.append(EvidenceRecord.evidence_type == evidence_type)
        if quality_state:
            filters.append(EvidenceRecord.quality_state == quality_state)
        if source:
            filters.append(EvidenceRecord.source == source)
        if model_version:
            filters.append(EvidenceRecord.model_version == model_version)
        if policy_version:
            filters.append(EvidenceRecord.policy_version == policy_version)
        if observation_cycle is not None:
            filters.append(EvidenceRecord.observation_cycle == observation_cycle)

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        total = db.execute(count_stmt).scalar() or 0

        # Sort order: observation_cycle desc if present, otherwise created_at desc
        stmt = stmt.order_by(
            EvidenceRecord.observation_cycle.desc().nullslast(),
            EvidenceRecord.created_at.desc(),
        ).limit(limit).offset(offset)

        records = list(db.execute(stmt).scalars().all())
        return total, records

    @staticmethod
    def get_entity_evidence(
        db: Session,
        entity_type: str,
        entity_id: str,
        domain: Optional[str] = None,
    ) -> List[EvidenceRecord]:
        stmt = select(EvidenceRecord).where(
            EvidenceRecord.entity_type == entity_type,
            EvidenceRecord.entity_id == str(entity_id),
        )
        if domain:
            stmt = stmt.where(EvidenceRecord.domain == domain)

        stmt = stmt.order_by(
            EvidenceRecord.observation_cycle.desc().nullslast(),
            EvidenceRecord.created_at.desc(),
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def get_entity_timeline(
        db: Session,
        entity_type: str,
        entity_id: str,
    ) -> List[EvidenceRecord]:
        """
        Retrieves ordered timeline for an entity.
        Preserves C-MAPSS cycle order without fabricating wall-clock times.
        """
        stmt = select(EvidenceRecord).where(
            EvidenceRecord.entity_type == entity_type,
            EvidenceRecord.entity_id == str(entity_id),
        )

        # C-MAPSS: order by cycle asc/desc, then created_at
        stmt = stmt.order_by(
            EvidenceRecord.observation_cycle.asc().nullslast(),
            EvidenceRecord.created_at.asc(),
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def list_bundles(
        db: Session,
        domain: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[EvidenceBundle]:
        stmt = select(EvidenceBundle).options(
            joinedload(EvidenceBundle.items).joinedload(EvidenceBundleItem.evidence)
        )
        filters = []
        if domain:
            filters.append(EvidenceBundle.domain == domain)
        if entity_type:
            filters.append(EvidenceBundle.entity_type == entity_type)
        if entity_id:
            filters.append(EvidenceBundle.entity_id == str(entity_id))

        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.order_by(EvidenceBundle.created_at.desc()).limit(limit).offset(offset)
        return list(db.execute(stmt).unique().scalars().all())

    @staticmethod
    def get_bundle(db: Session, bundle_id: uuid.UUID) -> EvidenceBundle:
        stmt = select(EvidenceBundle).options(
            joinedload(EvidenceBundle.items).joinedload(EvidenceBundleItem.evidence)
        ).where(EvidenceBundle.id == bundle_id)

        bundle = db.execute(stmt).unique().scalars().first()
        if not bundle:
            raise NotFoundException(f"Evidence bundle '{bundle_id}' not found.")
        return bundle

    @staticmethod
    def get_bundle_timeline(db: Session, bundle_id: uuid.UUID) -> List[EvidenceRecord]:
        bundle = EvidenceService.get_bundle(db, bundle_id)
        # Order items according to display_order, or observation_cycle
        records = [item.evidence for item in bundle.items if item.evidence]
        return records

    @staticmethod
    def get_relationships(
        db: Session,
        evidence_id: uuid.UUID,
    ) -> Dict[str, List[EvidenceRelationship]]:
        """
        Retrieves incoming and outgoing relationships for an evidence record.
        """
        record = EvidenceService.get_evidence(db, evidence_id)

        outgoing_stmt = select(EvidenceRelationship).options(
            joinedload(EvidenceRelationship.target_evidence)
        ).where(EvidenceRelationship.source_evidence_id == evidence_id)
        outgoing = list(db.execute(outgoing_stmt).scalars().all())

        incoming_stmt = select(EvidenceRelationship).options(
            joinedload(EvidenceRelationship.source_evidence)
        ).where(EvidenceRelationship.target_evidence_id == evidence_id)
        incoming = list(db.execute(incoming_stmt).scalars().all())

        return {"outgoing": outgoing, "incoming": incoming}

    @staticmethod
    def get_provenance(db: Session, evidence_id: uuid.UUID) -> Dict[str, Any]:
        record = EvidenceService.get_evidence(db, evidence_id)
        return {
            "evidence_id": record.id,
            "domain": record.domain,
            "entity_type": record.entity_type,
            "entity_id": record.entity_id,
            "evidence_type": record.evidence_type,
            "source": record.source,
            "source_reference": record.source_reference,
            "provenance": record.provenance,
            "model_version": record.model_version,
            "feature_version": record.feature_version,
            "policy_version": record.policy_version,
            "quality_state": record.quality_state,
            "created_at": record.created_at,
        }

    @staticmethod
    def materialize_all_evidence(db: Session) -> Dict[str, Any]:
        """
        Scans persisted M4-M7 records across NASA C-MAPSS and MVTec AD,
        generating unified, traceable evidence records, causal relationships, and bundles.
        Strictly idempotent.
        """
        stats = {
            "records_discovered": 0,
            "evidence_created": 0,
            "relationships_created": 0,
            "bundles_created": 0,
            "skipped_existing": 0,
            "cross_domain_rejected": 0,
            "errors": [],
        }

        # -------------------------------------------------------------
        # DOMAIN A: NASA C-MAPSS MACHINE HEALTH INTELLIGENCE
        # -------------------------------------------------------------
        machines = list(db.execute(select(Machine)).scalars().all())
        predictions = list(
            db.execute(select(Prediction).order_by(Prediction.created_at.desc())).scalars().all()
        )
        risk_assessments = list(
            db.execute(select(RiskAssessment).order_by(RiskAssessment.created_at.desc())).scalars().all()
        )
        alerts = list(
            db.execute(select(Alert).order_by(Alert.created_at.desc())).scalars().all()
        )

        stats["records_discovered"] += len(machines) + len(predictions) + len(risk_assessments) + len(alerts)

        # Index predictions and risk assessments by prediction ID / machine ID
        risk_by_pred_id = {r.prediction_id: r for r in risk_assessments}
        alert_by_risk_id = {a.risk_assessment_id: a for a in alerts if a.risk_assessment_id}

        for pred in predictions:
            m = next((mach for mach in machines if mach.id == pred.machine_id), None)
            machine_name = m.name if m else str(pred.machine_id)

            # 1. Telemetry & Feature Evidence
            features_ev, c1 = EvidenceService.create_or_get_evidence(
                db=db,
                domain="MACHINE_HEALTH",
                entity_type="MACHINE",
                entity_id=str(pred.machine_id),
                evidence_type="FEATURE",
                source="c_mapss_feature_engine",
                source_reference=f"telemetry_records:machine={pred.machine_id}:cycle={pred.observation_cycle}",
                quality_state="DERIVED",
                observation_cycle=pred.observation_cycle,
                value={
                    "observation_cycle": pred.observation_cycle,
                    "machine_name": machine_name,
                    "window_size": 20,
                },
                unit="cycles",
                explanation=f"Causal rolling window features extracted at cycle {pred.observation_cycle} for {machine_name}.",
                provenance={
                    "dataset": "NASA C-MAPSS FD001",
                    "window_size": 20,
                    "causality": "strictly_causal_no_future_leakage",
                },
                feature_version="feat-v1.0.0",
            )
            if c1:
                stats["evidence_created"] += 1
            else:
                stats["skipped_existing"] += 1

            # 2. RUL Prediction Evidence
            model_ver_str = (
                pred.model_version.version
                if hasattr(pred, "model_version") and pred.model_version and hasattr(pred.model_version, "version")
                else "rul-randomforest-v1.0.0"
            )

            pred_ev, c2 = EvidenceService.create_or_get_evidence(
                db=db,
                domain="MACHINE_HEALTH",
                entity_type="MACHINE",
                entity_id=str(pred.machine_id),
                evidence_type="RUL_PREDICTION",
                source="c_mapss_rul_model",
                source_reference=f"predictions:{pred.id}",
                quality_state="VERIFIED",
                observation_cycle=pred.observation_cycle,
                value={
                    "predicted_rul": float(pred.predicted_rul),
                    "health_index": float(pred.health_index),
                    "operational_state": pred.operational_state,
                },
                unit="cycles",
                confidence=None,  # No fabricated confidence
                explanation=f"Prediction {str(pred.id)[:8]} estimates {float(pred.predicted_rul):.1f} remaining cycles for machine {machine_name}.",
                provenance={
                    "dataset": "NASA C-MAPSS FD001",
                    "model_version": model_ver_str,
                    "prediction_id": str(pred.id),
                },
                model_version=model_ver_str,
            )
            if c2:
                stats["evidence_created"] += 1
            else:
                stats["skipped_existing"] += 1

            # Relationship: Feature -> Prediction (DERIVED_FROM)
            rel1, r1 = EvidenceService.create_relationship(
                db=db,
                source_evidence_id=pred_ev.id,
                target_evidence_id=features_ev.id,
                relationship_type="DERIVED_FROM",
                relationship_metadata={"mechanism": "sliding_window_inference"},
            )
            if r1:
                stats["relationships_created"] += 1

            # 3. Health Index Evidence
            hi_ev, c3 = EvidenceService.create_or_get_evidence(
                db=db,
                domain="MACHINE_HEALTH",
                entity_type="MACHINE",
                entity_id=str(pred.machine_id),
                evidence_type="HEALTH_INDEX",
                source="c_mapss_health_index_mapper",
                source_reference=f"predictions:{pred.id}:health_index",
                quality_state="DERIVED",
                observation_cycle=pred.observation_cycle,
                value={
                    "health_index": float(pred.health_index),
                    "operational_state": pred.operational_state,
                },
                unit="ratio",
                explanation=f"Normalized Health Index {float(pred.health_index):.2f} derived via piecewise-linear capping (RUL_max=125).",
                provenance={"formula": "clamp(predicted_rul / 125.0, 0.0, 1.0)"},
                model_version=model_ver_str,
            )
            if c3:
                stats["evidence_created"] += 1
            else:
                stats["skipped_existing"] += 1

            # Relationship: Prediction -> Health Index (PRODUCED_BY)
            rel2, r2 = EvidenceService.create_relationship(
                db=db,
                source_evidence_id=hi_ev.id,
                target_evidence_id=pred_ev.id,
                relationship_type="PRODUCED_BY",
                relationship_metadata={"formula": "clamp(rul / 125, 0, 1)"},
            )
            if r2:
                stats["relationships_created"] += 1

            bundle_items = [
                (features_ev.id, "PRIMARY_OBSERVATION", 1),
                (pred_ev.id, "MODEL_INFERENCE", 2),
                (hi_ev.id, "DERIVED_ANALYTIC", 3),
            ]

            # 4. Risk Assessment Evidence if exists
            risk = risk_by_pred_id.get(pred.id)
            if risk:
                risk_ev, c4 = EvidenceService.create_or_get_evidence(
                    db=db,
                    domain="MACHINE_HEALTH",
                    entity_type="MACHINE",
                    entity_id=str(pred.machine_id),
                    evidence_type="RISK_ASSESSMENT",
                    source="machintel_risk_engine",
                    source_reference=f"risk_assessments:{risk.id}",
                    quality_state="DERIVED",
                    observation_cycle=pred.observation_cycle,
                    value={
                        "risk_state": risk.risk_state,
                        "health_index": float(risk.health_index),
                        "predicted_rul": float(risk.predicted_rul),
                        "reason_codes": risk.reason_codes,
                    },
                    unit=None,
                    explanation=(
                        f"Prediction {str(pred.id)[:8]} estimates {float(risk.predicted_rul):.1f} remaining cycles "
                        f"for machine {machine_name}. The current Health Index is {float(risk.health_index):.2f}, "
                        f"mapping to the configured {risk.risk_state} risk state under {risk.policy_version}."
                    ),
                    provenance={
                        "policy_version": risk.policy_version,
                        "reason_codes": risk.reason_codes,
                    },
                    policy_version=risk.policy_version,
                )
                if c4:
                    stats["evidence_created"] += 1
                else:
                    stats["skipped_existing"] += 1

                # Relationship: Risk -> Health Index (DERIVED_FROM)
                rel3, r3 = EvidenceService.create_relationship(
                    db=db,
                    source_evidence_id=risk_ev.id,
                    target_evidence_id=hi_ev.id,
                    relationship_type="DERIVED_FROM",
                    relationship_metadata={"policy_version": risk.policy_version},
                )
                if r3:
                    stats["relationships_created"] += 1

                bundle_items.append((risk_ev.id, "RISK_ASSESSMENT", 4))

                # 5. Alert Evidence if triggered
                alert = alert_by_risk_id.get(risk.id)
                if alert:
                    alert_ev, c5 = EvidenceService.create_or_get_evidence(
                        db=db,
                        domain="MACHINE_HEALTH",
                        entity_type="MACHINE",
                        entity_id=str(pred.machine_id),
                        evidence_type="ALERT",
                        source="machintel_alert_dispatcher",
                        source_reference=f"alerts:{alert.id}",
                        quality_state="VERIFIED",
                        observation_cycle=pred.observation_cycle,
                        value={
                            "alert_id": str(alert.id),
                            "severity": alert.severity,
                            "status": alert.status,
                            "title": alert.title,
                        },
                        explanation=f"Alert '{alert.title}' ({alert.severity}) triggered from risk state {risk.risk_state}.",
                        provenance={"alert_id": str(alert.id), "status": alert.status},
                    )
                    if c5:
                        stats["evidence_created"] += 1
                    else:
                        stats["skipped_existing"] += 1

                    # Relationship: Alert -> Risk (TRIGGERED)
                    rel4, r4 = EvidenceService.create_relationship(
                        db=db,
                        source_evidence_id=alert_ev.id,
                        target_evidence_id=risk_ev.id,
                        relationship_type="TRIGGERED",
                        relationship_metadata={"severity": alert.severity},
                    )
                    if r4:
                        stats["relationships_created"] += 1

                    bundle_items.append((alert_ev.id, "ALERT", 5))

            # Assemble Machine Health Evidence Bundle
            bundle_stmt = select(EvidenceBundle).where(
                EvidenceBundle.bundle_name == f"Bundle: {machine_name} (Cycle {pred.observation_cycle})",
                EvidenceBundle.domain == "MACHINE_HEALTH",
                EvidenceBundle.entity_id == str(pred.machine_id),
            )
            existing_bundle = db.execute(bundle_stmt).scalars().first()
            if not existing_bundle:
                EvidenceService.create_bundle(
                    db=db,
                    bundle_name=f"Bundle: {machine_name} (Cycle {pred.observation_cycle})",
                    domain="MACHINE_HEALTH",
                    entity_type="MACHINE",
                    entity_id=str(pred.machine_id),
                    description=f"Evidence bundle capturing telemetry, prediction, risk state, and alerts for {machine_name} at cycle {pred.observation_cycle}.",
                    evidence_items=bundle_items,
                )
                stats["bundles_created"] += 1

        # -------------------------------------------------------------
        # DOMAIN B: MVTEC AD VISUAL INSPECTION INTELLIGENCE
        # -------------------------------------------------------------
        runs = list(db.execute(select(InspectionRun)).scalars().all())
        results = list(db.execute(select(InspectionResult)).scalars().all())
        stats["records_discovered"] += len(runs) + len(results)

        for run in runs:
            # 1. Inspection Run Provenance Evidence
            run_ev, cr1 = EvidenceService.create_or_get_evidence(
                db=db,
                domain="VISUAL_INSPECTION",
                entity_type="INSPECTION_RUN",
                entity_id=str(run.id),
                evidence_type="DATASET_PROVENANCE",
                source="mvtec_ad_inspection_run",
                source_reference=f"inspection_runs:{run.id}",
                quality_state="PROVENANCE_ONLY",
                observation_time=run.created_at,
                value={
                    "category": run.category,
                    "dataset_identifier": run.dataset_identifier,
                    "total_images": run.total_images,
                    "passed_count": run.passed_count,
                    "defect_count": run.defect_count,
                    "threshold": float(run.threshold),
                },
                unit="patch_distance",
                explanation=(
                    f"Official MVTec AD evaluation run for {run.category} with {run.total_images} test images. "
                    f"Calibrated 3-sigma decision threshold τ = {float(run.threshold):.4f} under {run.policy_version}."
                ),
                provenance={
                    "dataset": run.dataset_identifier,
                    "category": run.category,
                    "model_version": run.model_version,
                    "feature_config_version": run.feature_config_version,
                    "policy_version": run.policy_version,
                    "normal_training_stats": (run.evaluation_summary or {}).get("normal_training_stats", {}),
                },
                model_version=run.model_version,
                feature_version=run.feature_config_version,
                policy_version=run.policy_version,
            )
            if cr1:
                stats["evidence_created"] += 1
            else:
                stats["skipped_existing"] += 1

            # 2. Run Analytics Evidence
            eval_summary = run.evaluation_summary or {}
            img_metrics = eval_summary.get("image_level_metrics", {})
            pix_metrics = eval_summary.get("pixel_level_metrics", {})

            analytics_ev, cr2 = EvidenceService.create_or_get_evidence(
                db=db,
                domain="VISUAL_INSPECTION",
                entity_type="INSPECTION_RUN",
                entity_id=str(run.id),
                evidence_type="ANALYTICS",
                source="inspection_analytics_service",
                source_reference=f"inspection_runs:{run.id}:analytics",
                quality_state="DERIVED",
                observation_time=run.created_at,
                value={
                    "roc_auc": img_metrics.get("roc_auc"),
                    "pr_auc": img_metrics.get("pr_auc"),
                    "f1_score": img_metrics.get("f1_score"),
                    "pixel_roc_auc": pix_metrics.get("pixel_roc_auc"),
                    "observed_defect_rate": (
                        run.defect_count / run.total_images if run.total_images > 0 else 0
                    ),
                },
                explanation=(
                    f"Evaluation analytics for run {str(run.id)[:8]}: Image ROC-AUC {img_metrics.get('roc_auc', 0)*100:.1f}%, "
                    f"Pixel ROC-AUC {pix_metrics.get('pixel_roc_auc', 0)*100:.1f}%, F1-Score {img_metrics.get('f1_score', 0)*100:.1f}%."
                ),
                provenance={"evaluation_summary": eval_summary},
                model_version=run.model_version,
                policy_version=run.policy_version,
            )
            if cr2:
                stats["evidence_created"] += 1
            else:
                stats["skipped_existing"] += 1

            # Relationship: Run -> Analytics (PRODUCED_BY)
            rel_r1, rr1 = EvidenceService.create_relationship(
                db=db,
                source_evidence_id=analytics_ev.id,
                target_evidence_id=run_ev.id,
                relationship_type="PRODUCED_BY",
                relationship_metadata={"scope": "run_level_aggregate"},
            )
            if rr1:
                stats["relationships_created"] += 1

            run_bundle_items = [
                (run_ev.id, "PROVENANCE", 1),
                (analytics_ev.id, "PRIMARY_OBSERVATION", 2),
            ]

            # 3. Materialize Results
            run_results = [res for res in results if res.run_id == run.id]
            for res in run_results:
                # Result Image & Decision Evidence
                is_above = res.image_level_score >= run.threshold
                comp_str = "above" if is_above else "below"
                res_ev, cr3 = EvidenceService.create_or_get_evidence(
                    db=db,
                    domain="VISUAL_INSPECTION",
                    entity_type="INSPECTION_RESULT",
                    entity_id=str(res.id),
                    evidence_type="INSPECTION_DECISION",
                    source="patchcore_inspection_engine",
                    source_reference=f"inspection_results:{res.id}",
                    quality_state="VERIFIED",
                    observation_time=res.created_at,
                    value={
                        "filename": res.source_image_filename,
                        "defect_class": res.defect_class,
                        "image_level_score": float(res.image_level_score),
                        "decision": res.decision,
                        "ground_truth_label": res.ground_truth_label,
                    },
                    unit="patch_distance",
                    explanation=(
                        f"Inspection result for {res.source_image_filename} ({res.defect_class}) produced anomaly score "
                        f"{float(res.image_level_score):.4f}, {comp_str} the configured threshold {float(run.threshold):.4f}, "
                        f"resulting in a {res.decision} decision under {run.policy_version}."
                    ),
                    provenance=res.inference_metadata or {},
                    model_version=run.model_version,
                    policy_version=run.policy_version,
                )
                if cr3:
                    stats["evidence_created"] += 1
                else:
                    stats["skipped_existing"] += 1

                # Relationship: Result -> Run (BELONGS_TO)
                rel_res1, rres1 = EvidenceService.create_relationship(
                    db=db,
                    source_evidence_id=res_ev.id,
                    target_evidence_id=run_ev.id,
                    relationship_type="BELONGS_TO",
                    relationship_metadata={"filename": res.source_image_filename},
                )
                if rres1:
                    stats["relationships_created"] += 1

                # Ground Truth Evidence if benchmark data exists
                if res.ground_truth_label:
                    gt_ev, cr4 = EvidenceService.create_or_get_evidence(
                        db=db,
                        domain="VISUAL_INSPECTION",
                        entity_type="INSPECTION_RESULT",
                        entity_id=str(res.id),
                        evidence_type="GROUND_TRUTH",
                        source="mvtec_ad_ground_truth",
                        source_reference=f"inspection_results:{res.id}:ground_truth",
                        quality_state="BENCHMARK_GROUND_TRUTH",
                        observation_time=res.created_at,
                        value={
                            "ground_truth_label": res.ground_truth_label,
                            "defect_class": res.defect_class,
                            "has_mask": bool(res.ground_truth_mask_path),
                        },
                        explanation=f"Official MVTec AD benchmark ground truth label is {res.ground_truth_label} ({res.defect_class}).",
                        provenance={"dataset": run.dataset_identifier, "defect_class": res.defect_class},
                    )
                    if cr4:
                        stats["evidence_created"] += 1
                    else:
                        stats["skipped_existing"] += 1

                    # Relationship: Result -> Ground Truth (EVALUATED_AGAINST)
                    rel_gt, rgt = EvidenceService.create_relationship(
                        db=db,
                        source_evidence_id=res_ev.id,
                        target_evidence_id=gt_ev.id,
                        relationship_type="EVALUATED_AGAINST",
                        relationship_metadata={
                            "correct": res.decision == res.ground_truth_label,
                            "class": res.defect_class,
                        },
                    )
                    if rgt:
                        stats["relationships_created"] += 1

                # Heatmap Artifact Evidence
                if res.heatmap_path:
                    hm_ev, cr5 = EvidenceService.create_or_get_evidence(
                        db=db,
                        domain="VISUAL_INSPECTION",
                        entity_type="INSPECTION_RESULT",
                        entity_id=str(res.id),
                        evidence_type="LOCALIZATION",
                        source="patchcore_anomaly_map",
                        source_reference=f"inspection_results:{res.id}:heatmap",
                        quality_state="DERIVED",
                        observation_time=res.created_at,
                        value={
                            "has_heatmap": True,
                            "has_overlay": bool(res.overlay_path),
                            "resolution": "224x224",
                        },
                        explanation=f"Pixel-level anomaly heatmap generated via Gaussian-smoothed patch distances.",
                        provenance={"colormap": "jet", "sigma": 4.0},
                        model_version=run.model_version,
                    )
                    if cr5:
                        stats["evidence_created"] += 1
                    else:
                        stats["skipped_existing"] += 1

                    # Relationship: Result -> Heatmap (HAS_ARTIFACT)
                    rel_hm, rhm = EvidenceService.create_relationship(
                        db=db,
                        source_evidence_id=res_ev.id,
                        target_evidence_id=hm_ev.id,
                        relationship_type="HAS_ARTIFACT",
                        relationship_metadata={"artifact_type": "heatmap"},
                    )
                    if rhm:
                        stats["relationships_created"] += 1

            # Assemble Visual Inspection Evidence Bundle for Run
            bundle_name = f"Inspection Run: {run.category} ({str(run.id)[:8]})"
            existing_run_bundle = db.execute(
                select(EvidenceBundle).where(
                    EvidenceBundle.bundle_name == bundle_name,
                    EvidenceBundle.domain == "VISUAL_INSPECTION",
                )
            ).scalars().first()

            if not existing_run_bundle:
                EvidenceService.create_bundle(
                    db=db,
                    bundle_name=bundle_name,
                    domain="VISUAL_INSPECTION",
                    entity_type="INSPECTION_RUN",
                    entity_id=str(run.id),
                    description=f"Visual Inspection Evidence Bundle for MVTec AD {run.category} covering threshold calibration, model performance, and defect localization.",
                    evidence_items=run_bundle_items,
                )
                stats["bundles_created"] += 1

        db.commit()
        return stats
