from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid
from fastapi import HTTPException, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.logging import logger
from backend.app.models.alert import Alert
from backend.app.models.audit import AuditLog
from backend.app.models.evidence import EvidenceRecord, EvidenceRelationship
from backend.app.models.inspection import InspectionResult
from backend.app.models.machine import Machine
from backend.app.models.maintenance import (
    MaintenanceEvent,
    MaintenancePriority,
    MaintenanceSourceDomain,
    MaintenanceSourceType,
    MaintenanceStatus,
    MaintenanceWorkOrder,
)
from backend.app.models.risk import RiskAssessment
from backend.app.models.user import User
from backend.app.schemas.maintenance import MaintenanceWorkOrderCreate
from backend.app.services.evidence_service import EvidenceService

MAINTENANCE_POLICY_VERSION = "maintenance-policy-v1.0.0"


class MaintenanceService:
    """
    Deterministic Maintenance Workflow and Decision-Support Service.
    Enforces evidence lineage, policy-driven prioritization, deduplication,
    strict domain separation, immutable audit trails, and human-in-the-loop lifecycle.
    """

    @staticmethod
    def create_work_order(
        db: Session,
        payload: MaintenanceWorkOrderCreate,
        current_user: Optional[User] = None,
    ) -> Tuple[MaintenanceWorkOrder, bool]:
        """
        Creates or retrieves an existing active MaintenanceWorkOrder grounded in authentic evidence.
        Returns (work_order, is_new: bool).
        """
        # 1. Validate Source and derive context
        source_ref_str = payload.source_reference.strip()
        try:
            source_uuid = uuid.UUID(source_ref_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Source reference '{source_ref_str}' must be a valid UUID.",
            )

        machine_id = payload.machine_id
        risk_state_at_creation: Optional[str] = None
        predicted_rul_at_creation: Optional[float] = None
        health_index_at_creation: Optional[float] = None
        anomaly_score_at_creation: Optional[float] = None
        default_title: str = ""
        default_description: str = ""
        default_priority: MaintenancePriority = MaintenancePriority.MEDIUM
        default_action: str = ""
        default_reason: str = ""
        evidence_refs: List[Dict[str, Any]] = []

        if payload.source_domain == MaintenanceSourceDomain.MACHINE_HEALTH:
            if payload.source_type == MaintenanceSourceType.RISK_ASSESSMENT:
                assessment = db.get(RiskAssessment, source_uuid)
                if not assessment:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"RiskAssessment with ID '{source_ref_str}' does not exist.",
                    )
                if assessment.risk_state == "NORMAL":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot create maintenance recommendation for asset in NORMAL risk state. Policy requires WATCH, ELEVATED, or CRITICAL.",
                    )

                # Resolve machine identifier
                machine_obj = db.get(Machine, assessment.machine_id)
                machine_id = machine_obj.machine_id if machine_obj else str(assessment.machine_id)
                risk_state_at_creation = assessment.risk_state
                predicted_rul_at_creation = assessment.predicted_rul
                health_index_at_creation = assessment.health_index

                # Priority and text policies
                if assessment.risk_state == "CRITICAL":
                    default_priority = MaintenancePriority.CRITICAL
                    default_action = "Prioritize human review of the machine-health evidence and assess whether maintenance action is required."
                    default_title = f"CRITICAL: Machine Health Action Required for {machine_id}"
                elif assessment.risk_state == "ELEVATED":
                    default_priority = MaintenancePriority.HIGH
                    default_action = "Review recent machine-health evidence and schedule inspection according to site maintenance procedures."
                    default_title = f"HIGH: Machine Health Inspection for {machine_id}"
                elif assessment.risk_state == "WATCH":
                    default_priority = MaintenancePriority.LOW
                    default_action = "Review recent machine-health trend and schedule routine check according to site maintenance procedures."
                    default_title = f"WATCH: Machine Health Monitoring for {machine_id}"
                else:
                    default_priority = MaintenancePriority.MEDIUM
                    default_action = "Review machine-health telemetry and verify operational parameters."
                    default_title = f"Machine Health Review for {machine_id}"

                default_reason = (
                    f"Machine {machine_id} exhibits {assessment.risk_state} risk state with estimated RUL of "
                    f"{assessment.predicted_rul:.1f} cycles and Health Index {assessment.health_index:.3f} "
                    f"(evaluated under {assessment.policy_version}). Reason codes: {', '.join(assessment.reason_codes or [])}."
                )
                default_description = (
                    f"Deterministic maintenance recommendation generated from RiskAssessment {source_ref_str}. "
                    f"Asset {machine_id} evaluated under policy {assessment.policy_version}."
                )
                evidence_refs.append({
                    "entity_type": "RISK_ASSESSMENT",
                    "id": str(assessment.id),
                    "risk_state": assessment.risk_state,
                    "rul": assessment.predicted_rul,
                    "health_index": assessment.health_index,
                })

            elif payload.source_type == MaintenanceSourceType.ALERT:
                alert = db.get(Alert, source_uuid)
                if not alert:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Alert with ID '{source_ref_str}' does not exist.",
                    )
                machine_obj = db.get(Machine, alert.machine_id)
                machine_id = machine_obj.machine_id if machine_obj else str(alert.machine_id)
                default_priority = MaintenancePriority.CRITICAL if alert.severity == "CRITICAL" else MaintenancePriority.HIGH
                default_title = f"Alert Escalation: {alert.title}"
                default_description = f"Maintenance work order escalated from active Alert {source_ref_str}: {alert.description}"
                default_action = "Prioritize human review of the machine-health evidence and assess whether maintenance action is required."
                default_reason = f"Active alert '{alert.title}' in severity {alert.severity}. Reason codes: {', '.join(alert.reason_codes or [])}."
                evidence_refs.append({
                    "entity_type": "ALERT",
                    "id": str(alert.id),
                    "severity": alert.severity,
                    "risk_assessment_id": str(alert.risk_assessment_id) if alert.risk_assessment_id else None,
                })

            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Source type '{payload.source_type}' is not supported for MACHINE_HEALTH domain.",
                )

        elif payload.source_domain == MaintenanceSourceDomain.VISUAL_INSPECTION:
            if payload.source_type == MaintenanceSourceType.INSPECTION_RESULT:
                result = db.get(InspectionResult, source_uuid)
                if not result:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"InspectionResult with ID '{source_ref_str}' does not exist.",
                    )
                if result.decision != "DEFECT":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot create maintenance recommendation for non-defective inspection result. Decision is PASS.",
                    )

                anomaly_score_at_creation = result.image_level_score
                default_priority = MaintenancePriority.HIGH
                default_action = "Review the inspection image, anomaly localization, and benchmark/model evidence before determining the appropriate maintenance or inspection action."
                threshold_val = result.run.threshold if result.run else 0.5
                default_title = f"Inspect Defective Metal Nut ({result.defect_class or 'anomaly'})"
                default_reason = (
                    f"Industrial vision pipeline detected defect class '{result.defect_class or 'unknown'}' "
                    f"with anomaly score {result.image_level_score:.4f} (threshold: {threshold_val:.4f}). "
                    f"Component inspection failed quality criteria."
                )
                default_description = (
                    f"Visual inspection work order generated from InspectionResult {source_ref_str}. "
                    f"Defect class: {result.defect_class}. Image path: {result.source_image_path}."
                )
                evidence_refs.append({
                    "entity_type": "INSPECTION_RESULT",
                    "id": str(result.id),
                    "run_id": str(result.run_id),
                    "defect_class": result.defect_class,
                    "anomaly_score": result.image_level_score,
                    "threshold": threshold_val,
                })
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Source type '{payload.source_type}' is not supported for VISUAL_INSPECTION domain.",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported source domain '{payload.source_domain}'.",
            )

        # 2. Deduplication check
        dedup_key = f"{payload.source_type.value}:{source_ref_str}:{MAINTENANCE_POLICY_VERSION}"
        existing_active = db.execute(
            select(MaintenanceWorkOrder).where(
                MaintenanceWorkOrder.deduplication_key == dedup_key,
                MaintenanceWorkOrder.status.in_([
                    MaintenanceStatus.OPEN.value,
                    MaintenanceStatus.ACKNOWLEDGED.value,
                    MaintenanceStatus.IN_PROGRESS.value,
                ]),
            )
        ).scalar_one_or_none()

        if existing_active:
            logger.info(
                f"Maintenance work order already exists for key '{dedup_key}' (ID: {existing_active.id}). Returning existing."
            )
            return existing_active, False

        # 3. Create new MaintenanceWorkOrder
        title = payload.title or default_title
        description = payload.description or default_description
        priority = (payload.priority.value if payload.priority else default_priority.value)
        recommended_action = payload.recommended_action or default_action
        reason = payload.reason or default_reason

        work_order = MaintenanceWorkOrder(
            id=uuid.uuid4(),
            machine_id=machine_id,
            source_domain=payload.source_domain.value,
            source_type=payload.source_type.value,
            source_reference=source_ref_str,
            deduplication_key=dedup_key,
            title=title,
            description=description,
            priority=priority,
            status=MaintenanceStatus.OPEN.value,
            recommended_action=recommended_action,
            reason=reason,
            risk_state_at_creation=risk_state_at_creation,
            predicted_rul_at_creation=predicted_rul_at_creation,
            health_index_at_creation=health_index_at_creation,
            anomaly_score_at_creation=anomaly_score_at_creation,
            policy_version=MAINTENANCE_POLICY_VERSION,
            evidence_references=evidence_refs,
            created_by_id=current_user.id if current_user else None,
            assigned_to_id=payload.assigned_to_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(work_order)
        db.flush()

        # 4. Create initial immutable MaintenanceEvent
        creation_event = MaintenanceEvent(
            id=uuid.uuid4(),
            work_order_id=work_order.id,
            event_type="CREATED",
            from_status=None,
            to_status=MaintenanceStatus.OPEN.value,
            actor_id=current_user.id if current_user else None,
            notes="Maintenance work order drafted from validated operational evidence.",
            event_metadata={
                "source_domain": payload.source_domain.value,
                "source_type": payload.source_type.value,
                "source_reference": source_ref_str,
                "policy_version": MAINTENANCE_POLICY_VERSION,
            },
            created_at=datetime.now(timezone.utc),
        )
        db.add(creation_event)

        # 5. Create AuditLog entry
        audit_entry = AuditLog(
            id=uuid.uuid4(),
            actor_id=current_user.id if current_user else None,
            action="MAINTENANCE_WORK_ORDER_CREATED",
            target_type="MAINTENANCE_WORK_ORDER",
            target_id=str(work_order.id),
            details={
                "source_domain": payload.source_domain.value,
                "source_type": payload.source_type.value,
                "source_reference": source_ref_str,
                "priority": priority,
                "status": MaintenanceStatus.OPEN.value,
                "deduplication_key": dedup_key,
            },
            created_at=datetime.now(timezone.utc),
        )
        db.add(audit_entry)

        # 6. Register Evidence Record & Lineage
        try:
            rec, _ = EvidenceService.create_or_get_evidence(
                db=db,
                domain=payload.source_domain.value,
                entity_type="MAINTENANCE_WORK_ORDER",
                entity_id=str(work_order.id),
                evidence_type="MAINTENANCE_RECOMMENDATION",
                source="maintenance_service",
                source_reference=f"maintenance_work_orders:{work_order.id}",
                quality_state="DERIVED",
                explanation=reason,
                provenance={
                    "source_reference": source_ref_str,
                    "source_type": payload.source_type.value,
                    "deduplication_key": dedup_key,
                },
                policy_version=MAINTENANCE_POLICY_VERSION,
            )

            # Link relationship to source evidence record if present
            source_rec = db.execute(
                select(EvidenceRecord).where(
                    EvidenceRecord.domain == payload.source_domain.value,
                    EvidenceRecord.entity_id == source_ref_str,
                )
            ).scalars().first()

            if source_rec:
                EvidenceService.create_relationship(
                    db=db,
                    source_evidence_id=rec.id,
                    target_evidence_id=source_rec.id,
                    relationship_type="DERIVED_FROM",
                    relationship_metadata={"policy_version": MAINTENANCE_POLICY_VERSION},
                )
        except Exception as e:
            logger.warning(f"Could not link maintenance evidence record: {e}")

        db.commit()
        db.refresh(work_order)
        return work_order, True

    @staticmethod
    def recommend_from_risk(
        db: Session,
        risk_id: uuid.UUID,
        current_user: Optional[User] = None,
    ) -> Tuple[MaintenanceWorkOrder, bool]:
        """Creates a maintenance recommendation drafted from an authentic RiskAssessment record."""
        payload = MaintenanceWorkOrderCreate(
            source_domain=MaintenanceSourceDomain.MACHINE_HEALTH,
            source_type=MaintenanceSourceType.RISK_ASSESSMENT,
            source_reference=str(risk_id),
        )
        return MaintenanceService.create_work_order(db, payload, current_user)

    @staticmethod
    def recommend_from_inspection(
        db: Session,
        inspection_result_id: uuid.UUID,
        current_user: Optional[User] = None,
    ) -> Tuple[MaintenanceWorkOrder, bool]:
        """Creates a maintenance recommendation drafted from an authentic DEFECT InspectionResult."""
        payload = MaintenanceWorkOrderCreate(
            source_domain=MaintenanceSourceDomain.VISUAL_INSPECTION,
            source_type=MaintenanceSourceType.INSPECTION_RESULT,
            source_reference=str(inspection_result_id),
        )
        return MaintenanceService.create_work_order(db, payload, current_user)

    @staticmethod
    def acknowledge_work_order(
        db: Session,
        work_order_id: uuid.UUID,
        actor: User,
        assigned_to_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
    ) -> MaintenanceWorkOrder:
        """Transitions work order from OPEN -> ACKNOWLEDGED."""
        wo = db.get(MaintenanceWorkOrder, work_order_id)
        if not wo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MaintenanceWorkOrder '{work_order_id}' not found.",
            )

        if wo.status != MaintenanceStatus.OPEN.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot acknowledge work order in status '{wo.status}'. Expected status is 'OPEN'.",
            )

        now = datetime.now(timezone.utc)
        wo.status = MaintenanceStatus.ACKNOWLEDGED.value
        wo.acknowledged_at = now
        wo.updated_at = now
        if assigned_to_id:
            assigned_user = db.get(User, assigned_to_id)
            if not assigned_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Assigned user '{assigned_to_id}' not found.",
                )
            wo.assigned_to_id = assigned_to_id

        event = MaintenanceEvent(
            id=uuid.uuid4(),
            work_order_id=wo.id,
            event_type="ACKNOWLEDGED",
            from_status=MaintenanceStatus.OPEN.value,
            to_status=MaintenanceStatus.ACKNOWLEDGED.value,
            actor_id=actor.id,
            notes=notes or "Work order acknowledged by operator.",
            event_metadata={"assigned_to_id": str(assigned_to_id) if assigned_to_id else None},
            created_at=now,
        )
        db.add(event)

        audit = AuditLog(
            id=uuid.uuid4(),
            actor_id=actor.id,
            action="MAINTENANCE_WORK_ORDER_ACKNOWLEDGED",
            target_type="MAINTENANCE_WORK_ORDER",
            target_id=str(wo.id),
            details={"assigned_to_id": str(assigned_to_id) if assigned_to_id else None, "notes": notes},
            created_at=now,
        )
        db.add(audit)

        db.commit()
        db.refresh(wo)
        return wo

    @staticmethod
    def start_work_order(
        db: Session,
        work_order_id: uuid.UUID,
        actor: User,
        notes: Optional[str] = None,
    ) -> MaintenanceWorkOrder:
        """Transitions work order from ACKNOWLEDGED -> IN_PROGRESS."""
        wo = db.get(MaintenanceWorkOrder, work_order_id)
        if not wo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MaintenanceWorkOrder '{work_order_id}' not found.",
            )

        if wo.status != MaintenanceStatus.ACKNOWLEDGED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start work order in status '{wo.status}'. Expected status is 'ACKNOWLEDGED'.",
            )

        now = datetime.now(timezone.utc)
        wo.status = MaintenanceStatus.IN_PROGRESS.value
        wo.started_at = now
        wo.updated_at = now

        event = MaintenanceEvent(
            id=uuid.uuid4(),
            work_order_id=wo.id,
            event_type="STARTED",
            from_status=MaintenanceStatus.ACKNOWLEDGED.value,
            to_status=MaintenanceStatus.IN_PROGRESS.value,
            actor_id=actor.id,
            notes=notes or "Work order execution started.",
            event_metadata={},
            created_at=now,
        )
        db.add(event)

        audit = AuditLog(
            id=uuid.uuid4(),
            actor_id=actor.id,
            action="MAINTENANCE_WORK_ORDER_STARTED",
            target_type="MAINTENANCE_WORK_ORDER",
            target_id=str(wo.id),
            details={"notes": notes},
            created_at=now,
        )
        db.add(audit)

        db.commit()
        db.refresh(wo)
        return wo

    @staticmethod
    def complete_work_order(
        db: Session,
        work_order_id: uuid.UUID,
        actor: User,
        resolution_notes: str,
        notes: Optional[str] = None,
    ) -> MaintenanceWorkOrder:
        """Transitions work order from IN_PROGRESS -> COMPLETED with human-recorded outcome."""
        wo = db.get(MaintenanceWorkOrder, work_order_id)
        if not wo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MaintenanceWorkOrder '{work_order_id}' not found.",
            )

        if wo.status != MaintenanceStatus.IN_PROGRESS.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot complete work order in status '{wo.status}'. Expected status is 'IN_PROGRESS'.",
            )

        if not resolution_notes or len(resolution_notes.strip()) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resolution notes are required to complete a work order (minimum 3 characters).",
            )

        now = datetime.now(timezone.utc)
        wo.status = MaintenanceStatus.COMPLETED.value
        wo.completed_at = now
        wo.updated_at = now
        wo.resolution_notes = resolution_notes.strip()

        event = MaintenanceEvent(
            id=uuid.uuid4(),
            work_order_id=wo.id,
            event_type="COMPLETED",
            from_status=MaintenanceStatus.IN_PROGRESS.value,
            to_status=MaintenanceStatus.COMPLETED.value,
            actor_id=actor.id,
            notes=notes or resolution_notes.strip(),
            event_metadata={"resolution_notes": resolution_notes.strip()},
            created_at=now,
        )
        db.add(event)

        audit = AuditLog(
            id=uuid.uuid4(),
            actor_id=actor.id,
            action="MAINTENANCE_WORK_ORDER_COMPLETED",
            target_type="MAINTENANCE_WORK_ORDER",
            target_id=str(wo.id),
            details={"resolution_notes": resolution_notes.strip(), "notes": notes},
            created_at=now,
        )
        db.add(audit)

        # Register authentic MAINTENANCE_OUTCOME evidence record
        try:
            outcome_rec, _ = EvidenceService.create_or_get_evidence(
                db=db,
                domain=wo.source_domain,
                entity_type="MAINTENANCE_WORK_ORDER",
                entity_id=str(wo.id),
                evidence_type="MAINTENANCE_OUTCOME",
                source="maintenance_service",
                source_reference=f"maintenance_work_orders:{wo.id}:outcome",
                quality_state="VERIFIED",
                value={"status": "COMPLETED", "resolution_notes": resolution_notes.strip()},
                explanation=f"Work order completed by operator {actor.username}: {resolution_notes.strip()}",
                provenance={"completed_by_id": str(actor.id), "completed_at": now.isoformat()},
                policy_version=MAINTENANCE_POLICY_VERSION,
            )

            # Link relationship to the maintenance recommendation evidence
            wo_rec = db.execute(
                select(EvidenceRecord).where(
                    EvidenceRecord.domain == wo.source_domain,
                    EvidenceRecord.entity_type == "MAINTENANCE_WORK_ORDER",
                    EvidenceRecord.entity_id == str(wo.id),
                    EvidenceRecord.evidence_type == "MAINTENANCE_RECOMMENDATION",
                )
            ).scalars().first()

            if wo_rec:
                EvidenceService.create_relationship(
                    db=db,
                    source_evidence_id=outcome_rec.id,
                    target_evidence_id=wo_rec.id,
                    relationship_type="DOCUMENTS",
                    relationship_metadata={"resolution": "COMPLETED"},
                )
        except Exception as e:
            logger.warning(f"Could not record maintenance outcome evidence: {e}")

        db.commit()
        db.refresh(wo)
        return wo

    @staticmethod
    def cancel_work_order(
        db: Session,
        work_order_id: uuid.UUID,
        actor: User,
        reason: str,
        notes: Optional[str] = None,
    ) -> MaintenanceWorkOrder:
        """Transitions work order to CANCELLED from OPEN, ACKNOWLEDGED, or IN_PROGRESS."""
        wo = db.get(MaintenanceWorkOrder, work_order_id)
        if not wo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MaintenanceWorkOrder '{work_order_id}' not found.",
            )

        allowed_from = [
            MaintenanceStatus.OPEN.value,
            MaintenanceStatus.ACKNOWLEDGED.value,
            MaintenanceStatus.IN_PROGRESS.value,
        ]
        if wo.status not in allowed_from:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel work order in terminal status '{wo.status}'.",
            )

        if not reason or len(reason.strip()) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cancellation reason is required (minimum 3 characters).",
            )

        now = datetime.now(timezone.utc)
        prev_status = wo.status
        wo.status = MaintenanceStatus.CANCELLED.value
        wo.cancelled_at = now
        wo.updated_at = now
        wo.resolution_notes = f"CANCELLED: {reason.strip()}"

        event = MaintenanceEvent(
            id=uuid.uuid4(),
            work_order_id=wo.id,
            event_type="CANCELLED",
            from_status=prev_status,
            to_status=MaintenanceStatus.CANCELLED.value,
            actor_id=actor.id,
            notes=reason.strip(),
            event_metadata={"reason": reason.strip(), "extra_notes": notes},
            created_at=now,
        )
        db.add(event)

        audit = AuditLog(
            id=uuid.uuid4(),
            actor_id=actor.id,
            action="MAINTENANCE_WORK_ORDER_CANCELLED",
            target_type="MAINTENANCE_WORK_ORDER",
            target_id=str(wo.id),
            details={"from_status": prev_status, "reason": reason.strip(), "notes": notes},
            created_at=now,
        )
        db.add(audit)

        db.commit()
        db.refresh(wo)
        return wo

    @staticmethod
    def get_work_order(
        db: Session,
        work_order_id: uuid.UUID,
    ) -> MaintenanceWorkOrder:
        """Retrieves a single MaintenanceWorkOrder with events preloaded."""
        stmt = (
            select(MaintenanceWorkOrder)
            .options(selectinload(MaintenanceWorkOrder.events))
            .where(MaintenanceWorkOrder.id == work_order_id)
        )
        wo = db.execute(stmt).scalar_one_or_none()
        if not wo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MaintenanceWorkOrder '{work_order_id}' not found.",
            )
        return wo

    @staticmethod
    def list_work_orders(
        db: Session,
        status_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
        source_domain_filter: Optional[str] = None,
        machine_id_filter: Optional[str] = None,
        created_by_id: Optional[uuid.UUID] = None,
        assigned_to_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[MaintenanceWorkOrder], int]:
        """Lists maintenance work orders with filtering and pagination."""
        query = select(MaintenanceWorkOrder)

        if status_filter:
            query = query.where(MaintenanceWorkOrder.status == status_filter.upper())
        if priority_filter:
            query = query.where(MaintenanceWorkOrder.priority == priority_filter.upper())
        if source_domain_filter:
            query = query.where(MaintenanceWorkOrder.source_domain == source_domain_filter.upper())
        if machine_id_filter:
            query = query.where(MaintenanceWorkOrder.machine_id == machine_id_filter)
        if created_by_id:
            query = query.where(MaintenanceWorkOrder.created_by_id == created_by_id)
        if assigned_to_id:
            query = query.where(MaintenanceWorkOrder.assigned_to_id == assigned_to_id)

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total = db.scalar(count_stmt) or 0

        # Execute page
        items_stmt = query.order_by(desc(MaintenanceWorkOrder.created_at)).offset(skip).limit(limit)
        items = list(db.scalars(items_stmt).all())
        return items, total

    @staticmethod
    def get_summary(db: Session) -> Dict[str, Any]:
        """Calculates fleet-wide maintenance KPIs and recent activity."""
        # Counts by status
        status_counts = dict(
            db.execute(
                select(MaintenanceWorkOrder.status, func.count(MaintenanceWorkOrder.id)).group_by(
                    MaintenanceWorkOrder.status
                )
            ).all()
        )

        # Counts by priority
        priority_counts = dict(
            db.execute(
                select(MaintenanceWorkOrder.priority, func.count(MaintenanceWorkOrder.id)).group_by(
                    MaintenanceWorkOrder.priority
                )
            ).all()
        )

        # Counts by domain
        domain_counts = dict(
            db.execute(
                select(MaintenanceWorkOrder.source_domain, func.count(MaintenanceWorkOrder.id)).group_by(
                    MaintenanceWorkOrder.source_domain
                )
            ).all()
        )

        total_work_orders = sum(status_counts.values())

        # Recent events
        recent_events = list(
            db.scalars(
                select(MaintenanceEvent)
                .order_by(desc(MaintenanceEvent.created_at))
                .limit(10)
            ).all()
        )

        return {
            "total_work_orders": total_work_orders,
            "open_count": status_counts.get(MaintenanceStatus.OPEN.value, 0),
            "acknowledged_count": status_counts.get(MaintenanceStatus.ACKNOWLEDGED.value, 0),
            "in_progress_count": status_counts.get(MaintenanceStatus.IN_PROGRESS.value, 0),
            "completed_count": status_counts.get(MaintenanceStatus.COMPLETED.value, 0),
            "cancelled_count": status_counts.get(MaintenanceStatus.CANCELLED.value, 0),
            "critical_priority_count": priority_counts.get(MaintenancePriority.CRITICAL.value, 0),
            "high_priority_count": priority_counts.get(MaintenancePriority.HIGH.value, 0),
            "medium_priority_count": priority_counts.get(MaintenancePriority.MEDIUM.value, 0),
            "low_priority_count": priority_counts.get(MaintenancePriority.LOW.value, 0),
            "machine_health_count": domain_counts.get(MaintenanceSourceDomain.MACHINE_HEALTH.value, 0),
            "visual_inspection_count": domain_counts.get(MaintenanceSourceDomain.VISUAL_INSPECTION.value, 0),
            "recent_activity": recent_events,
        }
