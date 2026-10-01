from datetime import datetime, timezone
import re
from typing import Any, Callable, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from backend.app.core.errors import NotFoundException, ValidationException
from backend.app.core.logging import logger
from backend.app.models.alert import Alert
from backend.app.models.evidence import EvidenceBundle, EvidenceRecord, EvidenceRelationship
from backend.app.models.inspection import InspectionResult, InspectionRun
from backend.app.models.machine import Machine
from backend.app.models.maintenance import MaintenanceEvent, MaintenanceWorkOrder
from backend.app.models.prediction import Prediction
from backend.app.models.risk import RiskAssessment, RiskTransition
from backend.app.services.evidence_service import EvidenceService

# Security validation patterns
SQL_INJECTION_RE = re.compile(
    r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|EXEC|UNION|OR\s+1=1|AND\s+1=1)\b|--|;|\/\*|\*\/",
    re.IGNORECASE,
)
PATH_TRAVERSAL_RE = re.compile(r"\.\.|\/etc\/|\/var\/|\/proc\/|\\|\.env|\bpasswd\b", re.IGNORECASE)
MACHINE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,100}$")


def _sanitize_string(val: Optional[str], field_name: str) -> Optional[str]:
    if val is None:
        return None
    val_clean = val.strip()
    if SQL_INJECTION_RE.search(val_clean):
        raise ValidationException(
            message=f"Potentially unsafe input detected in parameter '{field_name}'.",
            details={"parameter": field_name, "reason": "SQL keyword pattern detected"},
        )
    if PATH_TRAVERSAL_RE.search(val_clean):
        raise ValidationException(
            message=f"Path traversal characters detected in parameter '{field_name}'.",
            details={"parameter": field_name, "reason": "Path traversal pattern detected"},
        )
    return val_clean


def _validate_uuid(val: str, field_name: str) -> uuid.UUID:
    _sanitize_string(val, field_name)
    try:
        return uuid.UUID(str(val).strip())
    except (ValueError, AttributeError):
        raise ValidationException(
            message=f"Parameter '{field_name}' must be a valid UUID.",
            details={"parameter": field_name, "received": str(val)},
        )


def _validate_machine_id(val: str) -> str:
    cleaned = _sanitize_string(val, "machine_id")
    if not cleaned or not MACHINE_ID_RE.match(cleaned):
        raise ValidationException(
            message="Parameter 'machine_id' must consist of alphanumeric characters, hyphens, and underscores (max 100).",
            details={"machine_id": val},
        )
    return cleaned


class ToolDefinition(BaseModel):
    name: str
    description: str
    domain: str  # MACHINE_HEALTH, VISUAL_INSPECTION, CROSS_DOMAIN
    read_only: bool = True
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    func: Callable[..., Any] = Field(exclude=True)


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition):
        self._tools[definition.name] = definition

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._tools.values())


tool_registry = ToolRegistry()


# =====================================================================
# A. MACHINE TOOLS
# =====================================================================

def tool_get_machine(db: Session, machine_id: str) -> Dict[str, Any]:
    mid = _validate_machine_id(machine_id)
    stmt = select(Machine).where(Machine.machine_id == mid)
    m = db.execute(stmt).scalar_one_or_none()
    if not m:
        return {"found": False, "error": f"Machine '{mid}' not found."}
    return {
        "found": True,
        "machine_id": m.machine_id,
        "dataset_name": m.dataset_name,
        "machine_type": m.machine_type.value if hasattr(m.machine_type, "value") else str(m.machine_type),
        "status": m.status.value if hasattr(m.status, "value") else str(m.status),
        "split_category": m.split_category.value if hasattr(m.split_category, "value") else str(m.split_category),
        "total_cycles": m.total_cycles,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


def tool_get_machine_health_summary(db: Session, machine_id: str, observation_cycle: Optional[int] = None) -> Dict[str, Any]:
    mid = _validate_machine_id(machine_id)
    # Check machine exists
    m_stmt = select(Machine).where(Machine.machine_id == mid)
    m = db.execute(m_stmt).scalar_one_or_none()
    if not m:
        return {"found": False, "error": f"Machine '{mid}' not found."}

    # Query prediction using machine UUID
    pred_query = select(Prediction).where(Prediction.machine_id == m.id)
    if observation_cycle is not None:
        pred_query = pred_query.where(Prediction.observation_cycle == observation_cycle)
    pred_query = pred_query.order_by(desc(Prediction.observation_cycle)).limit(1)
    prediction = db.execute(pred_query).scalar_one_or_none()

    if not prediction:
        return {
            "found": True,
            "machine_id": mid,
            "health_summary": None,
            "message": "No prognostic predictions recorded for this machine.",
        }

    # Query latest risk assessment for this prediction
    risk_stmt = (
        select(RiskAssessment)
        .where(RiskAssessment.prediction_id == prediction.id)
        .order_by(desc(RiskAssessment.created_at))
        .limit(1)
    )
    risk_assessment = db.execute(risk_stmt).scalars().first()

    # Query linked EvidenceRecord if any
    ev_stmt = select(EvidenceRecord).where(
        EvidenceRecord.domain == "MACHINE_HEALTH",
        EvidenceRecord.entity_id == mid,
        EvidenceRecord.evidence_type.in_(["PREDICTION", "RISK_ASSESSMENT"]),
        EvidenceRecord.observation_cycle == prediction.observation_cycle,
    ).limit(2)
    ev_records = db.execute(ev_stmt).scalars().all()

    evidence_citations = [
        {
            "evidence_id": str(e.id),
            "domain": e.domain,
            "type": e.evidence_type,
            "quality_state": e.quality_state,
            "cycle": e.observation_cycle,
            "provenance_digest": e.provenance.get("digest") if isinstance(e.provenance, dict) else str(e.provenance),
        }
        for e in ev_records
    ]

    return {
        "found": True,
        "machine_id": mid,
        "observation_cycle": prediction.observation_cycle,
        "predicted_rul": prediction.predicted_rul,
        "health_index": prediction.health_index,
        "operational_state": prediction.operational_state.value if hasattr(prediction.operational_state, "value") else str(prediction.operational_state),
        "model_version_id": str(prediction.model_version_id),
        "risk_state": risk_assessment.risk_state if risk_assessment else "UNASSESSED",
        "reason_codes": risk_assessment.reason_codes if risk_assessment else [],
        "risk_policy_version": risk_assessment.policy_version if risk_assessment else None,
        "calibrated_confidence": None,  # Strictly uncalibrated baseline
        "evidence_citations": evidence_citations,
    }


def tool_get_machine_predictions(db: Session, machine_id: str, limit: int = 10) -> Dict[str, Any]:
    mid = _validate_machine_id(machine_id)
    m_stmt = select(Machine).where(Machine.machine_id == mid)
    m = db.execute(m_stmt).scalar_one_or_none()
    if not m:
        return {"found": False, "error": f"Machine '{mid}' not found.", "count": 0, "predictions": []}

    limit_bound = max(1, min(limit, 50))
    stmt = (
        select(Prediction)
        .where(Prediction.machine_id == m.id)
        .order_by(desc(Prediction.observation_cycle))
        .limit(limit_bound)
    )
    predictions = db.execute(stmt).scalars().all()
    return {
        "machine_id": mid,
        "count": len(predictions),
        "predictions": [
            {
                "id": str(p.id),
                "observation_cycle": p.observation_cycle,
                "predicted_rul": p.predicted_rul,
                "health_index": p.health_index,
                "operational_state": p.operational_state.value if hasattr(p.operational_state, "value") else str(p.operational_state),
                "model_version_id": str(p.model_version_id),
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in predictions
        ],
    }


def tool_get_machine_risk(db: Session, machine_id: str, history_limit: int = 10) -> Dict[str, Any]:
    mid = _validate_machine_id(machine_id)
    m_stmt = select(Machine).where(Machine.machine_id == mid)
    m = db.execute(m_stmt).scalar_one_or_none()
    if not m:
        return {"found": False, "error": f"Machine '{mid}' not found.", "current_risk_state": "UNKNOWN", "historical_assessments": [], "recent_transitions": []}

    limit_bound = max(1, min(history_limit, 50))

    # Query latest assessment
    stmt = (
        select(RiskAssessment)
        .where(RiskAssessment.machine_id == m.id)
        .order_by(desc(RiskAssessment.created_at))
        .limit(limit_bound)
    )
    assessments = db.execute(stmt).scalars().all()

    # Query transitions
    t_stmt = (
        select(RiskTransition)
        .where(RiskTransition.machine_id == m.id)
        .order_by(desc(RiskTransition.created_at))
        .limit(limit_bound)
    )
    transitions = db.execute(t_stmt).scalars().all()

    latest = assessments[0] if assessments else None
    latest_cycle = (latest.prediction.observation_cycle if (latest and latest.prediction) else None)
    return {
        "machine_id": mid,
        "current_risk_state": latest.risk_state if latest else "UNKNOWN",
        "current_policy_version": latest.policy_version if latest else None,
        "latest_reason_codes": latest.reason_codes if latest else [],
        "latest_cycle": latest_cycle,
        "historical_assessments": [
            {
                "id": str(a.id),
                "cycle": a.prediction.observation_cycle if a.prediction else None,
                "risk_state": a.risk_state,
                "reason_codes": a.reason_codes,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in assessments
        ],
        "recent_transitions": [
            {
                "from_state": t.from_state,
                "to_state": t.to_state,
                "trigger_cycle": t.trigger_cycle,
                "reason": t.reason,
                "timestamp": t.created_at.isoformat() if t.created_at else None,
            }
            for t in transitions
        ],
    }


# =====================================================================
# B. ALERT TOOLS
# =====================================================================

def tool_get_machine_alerts(db: Session, machine_id: str, status: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    mid = _validate_machine_id(machine_id)
    m_stmt = select(Machine).where(Machine.machine_id == mid)
    m = db.execute(m_stmt).scalar_one_or_none()
    if not m:
        return {"found": False, "error": f"Machine '{mid}' not found.", "count": 0, "alerts": []}

    status_clean = _sanitize_string(status, "status")
    limit_bound = max(1, min(limit, 50))

    query = select(Alert).where(Alert.machine_id == m.id)
    if status_clean:
        query = query.where(Alert.status == status_clean.upper())
    query = query.order_by(desc(Alert.created_at)).limit(limit_bound)

    alerts = db.execute(query).scalars().all()
    return {
        "machine_id": mid,
        "count": len(alerts),
        "alerts": [
            {
                "id": str(a.id),
                "severity": a.severity,
                "status": a.status,
                "title": a.title,
                "description": a.description,
                "reason_codes": a.reason_codes,
                "risk_state": a.risk_state,
                "policy_version": a.policy_version,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
            }
            for a in alerts
        ],
    }


# =====================================================================
# C. EVIDENCE TOOLS
# =====================================================================

def tool_search_evidence(
    db: Session,
    domain: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    evidence_type: Optional[str] = None,
    source: Optional[str] = None,
    quality_state: Optional[str] = None,
    observation_cycle: Optional[int] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    domain_clean = _sanitize_string(domain, "domain")
    entity_type_clean = _sanitize_string(entity_type, "entity_type")
    entity_id_clean = _sanitize_string(entity_id, "entity_id")
    evidence_type_clean = _sanitize_string(evidence_type, "evidence_type")
    source_clean = _sanitize_string(source, "source")
    quality_state_clean = _sanitize_string(quality_state, "quality_state")
    limit_bound = max(1, min(limit, 50))

    results, total = EvidenceService.search_evidence(
        db=db,
        domain=domain_clean.upper() if domain_clean else None,
        entity_type=entity_type_clean.upper() if entity_type_clean else None,
        entity_id=entity_id_clean,
        evidence_type=evidence_type_clean.upper() if evidence_type_clean else None,
        source=source_clean,
        quality_state=quality_state_clean.upper() if quality_state_clean else None,
        observation_cycle=observation_cycle,
        limit=limit_bound,
        offset=0,
    )

    return {
        "total": total,
        "returned": len(results),
        "evidence_records": [
            {
                "evidence_id": str(e.id),
                "domain": e.domain,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "evidence_type": e.evidence_type,
                "source": e.source,
                "source_reference": e.source_reference,
                "observation_cycle": e.observation_cycle,
                "quality_state": e.quality_state,
                "explanation": e.explanation,
                "provenance_digest": e.provenance.get("digest") if isinstance(e.provenance, dict) else str(e.provenance),
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in results
        ],
    }


def tool_get_evidence(db: Session, evidence_id: str) -> Dict[str, Any]:
    eid = _validate_uuid(evidence_id, "evidence_id")
    rec = db.get(EvidenceRecord, eid)
    if not rec:
        return {"found": False, "error": f"EvidenceRecord '{eid}' not found."}

    # Query incoming and outgoing relationships
    rel_in_stmt = select(EvidenceRelationship).where(EvidenceRelationship.target_evidence_id == eid)
    rel_out_stmt = select(EvidenceRelationship).where(EvidenceRelationship.source_evidence_id == eid)
    rels_in = db.execute(rel_in_stmt).scalars().all()
    rels_out = db.execute(rel_out_stmt).scalars().all()

    return {
        "found": True,
        "evidence_id": str(rec.id),
        "domain": rec.domain,
        "entity_type": rec.entity_type,
        "entity_id": rec.entity_id,
        "evidence_type": rec.evidence_type,
        "source": rec.source,
        "source_reference": rec.source_reference,
        "observation_cycle": rec.observation_cycle,
        "quality_state": rec.quality_state,
        "value": rec.value,
        "unit": rec.unit,
        "confidence": rec.confidence,
        "explanation": rec.explanation,
        "model_version": rec.model_version,
        "policy_version": rec.policy_version,
        "provenance_digest": rec.provenance.get("digest") if isinstance(rec.provenance, dict) else str(rec.provenance),
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
        "relationships": {
            "supported_by": [str(r.source_evidence_id) for r in rels_in],
            "supports": [str(r.target_evidence_id) for r in rels_out],
        },
    }


def tool_get_evidence_timeline(db: Session, domain: str, entity_type: str, entity_id: str, limit: int = 20) -> Dict[str, Any]:
    dom_clean = _sanitize_string(domain, "domain")
    ent_type_clean = _sanitize_string(entity_type, "entity_type")
    ent_id_clean = _sanitize_string(entity_id, "entity_id")
    limit_bound = max(1, min(limit, 50))

    timeline = EvidenceService.get_timeline(
        db=db,
        domain=dom_clean.upper() if dom_clean else "MACHINE_HEALTH",
        entity_type=ent_type_clean.upper() if ent_type_clean else "MACHINE",
        entity_id=ent_id_clean or "",
        limit=limit_bound,
    )
    return {
        "domain": dom_clean,
        "entity_type": ent_type_clean,
        "entity_id": ent_id_clean,
        "count": len(timeline),
        "timeline": [
            {
                "evidence_id": str(e.id),
                "evidence_type": e.evidence_type,
                "observation_cycle": e.observation_cycle,
                "quality_state": e.quality_state,
                "explanation": e.explanation,
                "value_summary": str(e.value) if e.value else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in timeline
        ],
    }


def tool_get_evidence_bundle(db: Session, bundle_id: str) -> Dict[str, Any]:
    bid = _validate_uuid(bundle_id, "bundle_id")
    bundle = db.get(EvidenceBundle, bid)
    if not bundle:
        return {"found": False, "error": f"EvidenceBundle '{bid}' not found."}

    # Query bundle items
    items_stmt = select(EvidenceRecord).join(
        EvidenceBundle.items
    ).where(EvidenceBundle.id == bid)
    # Alternatively query through relationships:
    items = bundle.items if hasattr(bundle, "items") and bundle.items else []
    item_details = []
    for bi in items:
        rec = getattr(bi, "evidence_record", None)
        if rec:
            item_details.append({
                "evidence_id": str(rec.id),
                "domain": rec.domain,
                "type": rec.evidence_type,
                "cycle": rec.observation_cycle,
                "quality_state": rec.quality_state,
            })

    return {
        "found": True,
        "bundle_id": str(bundle.id),
        "domain": bundle.domain,
        "entity_type": bundle.entity_type,
        "entity_id": bundle.entity_id,
        "bundle_type": bundle.bundle_type,
        "title": bundle.title,
        "description": bundle.description,
        "items_count": len(item_details),
        "items": item_details,
        "created_at": bundle.created_at.isoformat() if bundle.created_at else None,
    }


# =====================================================================
# D. INSPECTION TOOLS
# =====================================================================

def tool_get_inspection_runs(db: Session, limit: int = 10) -> Dict[str, Any]:
    limit_bound = max(1, min(limit, 50))
    stmt = select(InspectionRun).order_by(desc(InspectionRun.created_at)).limit(limit_bound)
    runs = db.execute(stmt).scalars().all()
    return {
        "count": len(runs),
        "runs": [
            {
                "run_id": str(r.id),
                "dataset_name": r.dataset_name,
                "split_name": r.split_name,
                "model_name": r.model_name,
                "model_version": r.model_version,
                "total_samples": r.total_samples,
                "pass_count": r.pass_count,
                "defect_count": r.defect_count,
                "threshold_applied": r.threshold_applied,
                "calibration_mean": r.calibration_mean,
                "calibration_std": r.calibration_std,
                "policy_version": r.policy_version,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ],
    }


def tool_get_inspection_run(db: Session, run_id: str) -> Dict[str, Any]:
    rid = _validate_uuid(run_id, "run_id")
    run = db.get(InspectionRun, rid)
    if not run:
        return {"found": False, "error": f"InspectionRun '{rid}' not found."}
    return {
        "found": True,
        "run_id": str(run.id),
        "dataset_name": run.dataset_name,
        "split_name": run.split_name,
        "model_name": run.model_name,
        "model_version": run.model_version,
        "total_samples": run.total_samples,
        "pass_count": run.pass_count,
        "defect_count": run.defect_count,
        "threshold_applied": run.threshold_applied,
        "calibration_mean": run.calibration_mean,
        "calibration_std": run.calibration_std,
        "policy_version": run.policy_version,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


def tool_get_inspection_results(
    db: Session,
    run_id: str,
    defect_class: Optional[str] = None,
    decision: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    rid = _validate_uuid(run_id, "run_id")
    defect_clean = _sanitize_string(defect_class, "defect_class")
    decision_clean = _sanitize_string(decision, "decision")
    limit_bound = max(1, min(limit, 50))

    query = select(InspectionResult).where(InspectionResult.run_id == rid)
    if defect_clean:
        query = query.where(InspectionResult.defect_class == defect_clean.lower())
    if decision_clean:
        query = query.where(InspectionResult.decision == decision_clean.upper())

    query = query.order_by(desc(InspectionResult.image_level_score)).limit(limit_bound)
    results = db.execute(query).scalars().all()

    return {
        "run_id": str(rid),
        "count": len(results),
        "results": [
            {
                "result_id": str(res.id),
                "sample_index": res.sample_index,
                "image_level_score": res.image_level_score,
                "decision": res.decision,
                "defect_class": res.defect_class,
                "is_ground_truth_defect": res.is_ground_truth_defect,
                "threshold_applied": res.threshold_applied,
                "has_pixel_mask": bool(res.ground_truth_mask_path),
            }
            for res in results
        ],
    }


def tool_get_inspection_result(db: Session, result_id: str) -> Dict[str, Any]:
    rid = _validate_uuid(result_id, "result_id")
    res = db.get(InspectionResult, rid)
    if not res:
        return {"found": False, "error": f"InspectionResult '{rid}' not found."}

    # Query linked EvidenceRecord
    ev_stmt = select(EvidenceRecord).where(
        EvidenceRecord.domain == "VISUAL_INSPECTION",
        EvidenceRecord.source_reference == str(rid),
    )
    ev = db.execute(ev_stmt).scalar_one_or_none()

    return {
        "found": True,
        "result_id": str(res.id),
        "run_id": str(res.run_id),
        "sample_index": res.sample_index,
        "image_level_score": res.image_level_score,
        "threshold_applied": res.threshold_applied,
        "decision": res.decision,
        "defect_class": res.defect_class,
        "is_ground_truth_defect": res.is_ground_truth_defect,
        "defect_pixel_count": res.defect_pixel_count,
        "pixel_roc_auc": res.pixel_roc_auc,
        "evidence_id": str(ev.id) if ev else None,
        "evidence_quality": ev.quality_state if ev else "UNREGISTERED",
        "provenance_digest": ev.provenance.get("digest") if (ev and isinstance(ev.provenance, dict)) else None,
    }


# =====================================================================
# E. MAINTENANCE TOOLS
# =====================================================================

def tool_get_maintenance_work_orders(
    db: Session,
    machine_id: Optional[str] = None,
    source_domain: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    mid = _validate_machine_id(machine_id) if machine_id else None
    dom_clean = _sanitize_string(source_domain, "source_domain")
    status_clean = _sanitize_string(status, "status")
    limit_bound = max(1, min(limit, 50))

    query = select(MaintenanceWorkOrder)
    if mid:
        query = query.where(MaintenanceWorkOrder.machine_id == mid)
    if dom_clean:
        query = query.where(MaintenanceWorkOrder.source_domain == dom_clean.upper())
    if status_clean:
        query = query.where(MaintenanceWorkOrder.status == status_clean.upper())

    query = query.order_by(desc(MaintenanceWorkOrder.created_at)).limit(limit_bound)
    orders = db.execute(query).scalars().all()

    return {
        "count": len(orders),
        "work_orders": [
            {
                "work_order_id": str(o.id),
                "machine_id": o.machine_id,
                "source_domain": o.source_domain,
                "source_type": o.source_type,
                "source_reference": o.source_reference,
                "title": o.title,
                "priority": o.priority,
                "status": o.status,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "completed_at": o.completed_at.isoformat() if o.completed_at else None,
            }
            for o in orders
        ],
    }


def tool_get_maintenance_work_order(db: Session, work_order_id: str) -> Dict[str, Any]:
    wid = _validate_uuid(work_order_id, "work_order_id")
    order = db.get(MaintenanceWorkOrder, wid)
    if not order:
        return {"found": False, "error": f"MaintenanceWorkOrder '{wid}' not found."}

    # Query events
    events_stmt = (
        select(MaintenanceEvent)
        .where(MaintenanceEvent.work_order_id == wid)
        .order_by(MaintenanceEvent.created_at.asc())
    )
    events = db.execute(events_stmt).scalars().all()

    return {
        "found": True,
        "work_order_id": str(order.id),
        "machine_id": order.machine_id,
        "source_domain": order.source_domain,
        "source_type": order.source_type,
        "source_reference": order.source_reference,
        "title": order.title,
        "description": order.description,
        "priority": order.priority,
        "status": order.status,
        "recommended_action": order.recommended_action,
        "reason": order.reason,
        "risk_state_at_creation": order.risk_state_at_creation,
        "predicted_rul_at_creation": order.predicted_rul_at_creation,
        "health_index_at_creation": order.health_index_at_creation,
        "anomaly_score_at_creation": order.anomaly_score_at_creation,
        "resolution_notes": order.resolution_notes,
        "evidence_references": order.evidence_references or [],
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "completed_at": order.completed_at.isoformat() if order.completed_at else None,
        "lifecycle_events": [
            {
                "event_type": e.event_type,
                "from_status": e.from_status,
                "to_status": e.to_status,
                "notes": e.notes,
                "timestamp": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }


# =====================================================================
# Tool Registry Population (All Read-Only)
# =====================================================================

tool_registry.register(
    ToolDefinition(
        name="get_machine",
        description="Retrieve machine metadata, status, dataset source, and total cycles by machine_id.",
        domain="MACHINE_HEALTH",
        read_only=True,
        input_schema={"machine_id": "string"},
        output_schema={"found": "bool", "machine_id": "string", "status": "string", "total_cycles": "int"},
        func=tool_get_machine,
    )
)

tool_registry.register(
    ToolDefinition(
        name="get_machine_health_summary",
        description="Retrieve latest health index, estimated RUL, operational risk state, and linked evidence citations for a machine.",
        domain="MACHINE_HEALTH",
        read_only=True,
        input_schema={"machine_id": "string", "observation_cycle": "optional int"},
        output_schema={"found": "bool", "health_index": "float", "predicted_rul": "float", "risk_state": "string", "reason_codes": "list"},
        func=tool_get_machine_health_summary,
    )
)

tool_registry.register(
    ToolDefinition(
        name="get_machine_predictions",
        description="Retrieve historical prognostic RUL and health index predictions for a machine.",
        domain="MACHINE_HEALTH",
        read_only=True,
        input_schema={"machine_id": "string", "limit": "optional int (default 10)"},
        output_schema={"machine_id": "string", "predictions": "list"},
        func=tool_get_machine_predictions,
    )
)

tool_registry.register(
    ToolDefinition(
        name="get_machine_risk",
        description="Retrieve current and historical risk assessments, policy version, and state transitions for a machine.",
        domain="MACHINE_HEALTH",
        read_only=True,
        input_schema={"machine_id": "string", "history_limit": "optional int (default 10)"},
        output_schema={"current_risk_state": "string", "historical_assessments": "list", "recent_transitions": "list"},
        func=tool_get_machine_risk,
    )
)

tool_registry.register(
    ToolDefinition(
        name="get_machine_alerts",
        description="Retrieve active and historical operational alerts for a machine with severity and lifecycle status.",
        domain="MACHINE_HEALTH",
        read_only=True,
        input_schema={"machine_id": "string", "status": "optional string (e.g. OPEN, ACKNOWLEDGED, RESOLVED)", "limit": "optional int"},
        output_schema={"machine_id": "string", "alerts": "list"},
        func=tool_get_machine_alerts,
    )
)

tool_registry.register(
    ToolDefinition(
        name="search_evidence",
        description="Search authoritative EvidenceRecords across domain, entity, cycle, and quality state filters.",
        domain="CROSS_DOMAIN",
        read_only=True,
        input_schema={
            "domain": "optional string (MACHINE_HEALTH or VISUAL_INSPECTION)",
            "entity_type": "optional string",
            "entity_id": "optional string",
            "evidence_type": "optional string",
            "observation_cycle": "optional int",
            "limit": "optional int (default 20)",
        },
        output_schema={"total": "int", "evidence_records": "list"},
        func=tool_search_evidence,
    )
)

tool_registry.register(
    ToolDefinition(
        name="get_evidence",
        description="Retrieve detailed EvidenceRecord and its relationship graph by evidence UUID.",
        domain="CROSS_DOMAIN",
        read_only=True,
        input_schema={"evidence_id": "string (UUID)"},
        output_schema={"found": "bool", "evidence_id": "string", "domain": "string", "quality_state": "string", "relationships": "dict"},
        func=tool_get_evidence,
    )
)

tool_registry.register(
    ToolDefinition(
        name="get_evidence_timeline",
        description="Retrieve chronological sequence of evidence observations for an entity.",
        domain="CROSS_DOMAIN",
        read_only=True,
        input_schema={"domain": "string", "entity_type": "string", "entity_id": "string", "limit": "optional int"},
        output_schema={"domain": "string", "timeline": "list"},
        func=tool_get_evidence_timeline,
    )
)

tool_registry.register(
    ToolDefinition(
        name="get_evidence_bundle",
        description="Retrieve an evidence bundle and its constituent items by bundle UUID.",
        domain="CROSS_DOMAIN",
        read_only=True,
        input_schema={"bundle_id": "string (UUID)"},
        output_schema={"found": "bool", "bundle_id": "string", "items": "list"},
        func=tool_get_evidence_bundle,
    )
)

tool_registry.register(
    ToolDefinition(
        name="get_inspection_runs",
        description="List optical visual inspection runs with calibration parameters, thresholds, and defect counts.",
        domain="VISUAL_INSPECTION",
        read_only=True,
        input_schema={"limit": "optional int (default 10)"},
        output_schema={"count": "int", "runs": "list"},
        func=tool_get_inspection_runs,
    )
)

tool_registry.register(
    ToolDefinition(
        name="get_inspection_run",
        description="Retrieve detailed metadata and evaluation parameters for a specific visual inspection run.",
        domain="VISUAL_INSPECTION",
        read_only=True,
        input_schema={"run_id": "string (UUID)"},
        output_schema={"found": "bool", "run_id": "string", "threshold_applied": "float"},
        func=tool_get_inspection_run,
    )
)

tool_registry.register(
    ToolDefinition(
        name="get_inspection_results",
        description="Retrieve evaluated image results for an inspection run, filterable by defect class or decision.",
        domain="VISUAL_INSPECTION",
        read_only=True,
        input_schema={"run_id": "string (UUID)", "defect_class": "optional string", "decision": "optional string", "limit": "optional int"},
        output_schema={"run_id": "string", "results": "list"},
        func=tool_get_inspection_results,
    )
)

tool_registry.register(
    ToolDefinition(
        name="get_inspection_result",
        description="Retrieve specific visual inspection result, anomaly score, threshold, decision, and defect localization details.",
        domain="VISUAL_INSPECTION",
        read_only=True,
        input_schema={"result_id": "string (UUID)"},
        output_schema={"found": "bool", "image_level_score": "float", "decision": "string", "defect_class": "string"},
        func=tool_get_inspection_result,
    )
)

tool_registry.register(
    ToolDefinition(
        name="get_maintenance_work_orders",
        description="Retrieve maintenance work orders filterable by machine_id, source domain, or status.",
        domain="CROSS_DOMAIN",
        read_only=True,
        input_schema={"machine_id": "optional string", "source_domain": "optional string", "status": "optional string", "limit": "optional int"},
        output_schema={"count": "int", "work_orders": "list"},
        func=tool_get_maintenance_work_orders,
    )
)

tool_registry.register(
    ToolDefinition(
        name="get_maintenance_work_order",
        description="Retrieve detailed maintenance work order, source evidence lineage, and lifecycle history by UUID.",
        domain="CROSS_DOMAIN",
        read_only=True,
        input_schema={"work_order_id": "string (UUID)"},
        output_schema={"found": "bool", "work_order_id": "string", "status": "string", "priority": "string", "lifecycle_events": "list"},
        func=tool_get_maintenance_work_order,
    )
)
