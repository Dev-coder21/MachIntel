from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.core.errors import BadRequestException, NotFoundException
from backend.app.models.user import User, UserRole
from backend.app.schemas.evidence import (
    EvidenceBundleResponse,
    EvidenceProvenanceResponse,
    EvidenceRecordResponse,
    EvidenceRelationshipResponse,
    EvidenceSearchResponse,
    EvidenceTimelineItem,
)
from backend.app.services.evidence_service import EvidenceService

router = APIRouter()


@router.get("", response_model=EvidenceSearchResponse)
def search_evidence(
    domain: Optional[str] = Query(None, description="Filter by domain (MACHINE_HEALTH | VISUAL_INSPECTION)"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (MACHINE | INSPECTION_RUN | INSPECTION_RESULT | PREDICTION | RISK_ASSESSMENT | ALERT)"),
    entity_id: Optional[str] = Query(None, description="Filter by specific entity ID"),
    evidence_type: Optional[str] = Query(None, description="Filter by evidence type (TELEMETRY | FEATURE | RUL_PREDICTION | HEALTH_INDEX | RISK_ASSESSMENT | ALERT | IMAGE | ANOMALY_SCORE | INSPECTION_DECISION | LOCALIZATION | GROUND_TRUTH | ANALYTICS | DATASET_PROVENANCE)"),
    quality_state: Optional[str] = Query(None, description="Filter by quality state (VERIFIED | DERIVED | BENCHMARK_GROUND_TRUTH | PROVENANCE_ONLY | UNAVAILABLE)"),
    source: Optional[str] = Query(None, description="Filter by source component"),
    model_version: Optional[str] = Query(None, description="Filter by model version"),
    policy_version: Optional[str] = Query(None, description="Filter by policy version"),
    observation_cycle: Optional[int] = Query(None, description="Filter by C-MAPSS observation cycle"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.VIEWER, UserRole.OPERATOR, UserRole.ADMIN])),
) -> EvidenceSearchResponse:
    """
    Search and filter unified evidence records across Machine Health and Visual Inspection domains.
    Strictly prevents arbitrary database querying.
    """
    total, records = EvidenceService.search_evidence(
        db=db,
        domain=domain,
        entity_type=entity_type,
        entity_id=entity_id,
        evidence_type=evidence_type,
        quality_state=quality_state,
        source=source,
        model_version=model_version,
        policy_version=policy_version,
        observation_cycle=observation_cycle,
        limit=limit,
        offset=offset,
    )
    return EvidenceSearchResponse(
        total=total,
        records=records,
        domain=domain,
    )


@router.get("/bundles", response_model=List[EvidenceBundleResponse])
def list_evidence_bundles(
    domain: Optional[str] = Query(None, description="Filter bundles by domain"),
    entity_type: Optional[str] = Query(None, description="Filter bundles by entity type"),
    entity_id: Optional[str] = Query(None, description="Filter bundles by entity ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.VIEWER, UserRole.OPERATOR, UserRole.ADMIN])),
) -> List[EvidenceBundleResponse]:
    """
    List structured Evidence Bundles grouping domain-aligned observations and inferences.
    """
    bundles = EvidenceService.list_bundles(
        db=db,
        domain=domain,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        offset=offset,
    )
    return bundles


@router.get("/bundles/{bundle_id}", response_model=EvidenceBundleResponse)
def get_evidence_bundle(
    bundle_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.VIEWER, UserRole.OPERATOR, UserRole.ADMIN])),
) -> EvidenceBundleResponse:
    """
    Retrieve an Evidence Bundle with its constituent items and roles.
    """
    return EvidenceService.get_bundle(db, bundle_id)


@router.get("/bundles/{bundle_id}/timeline", response_model=List[EvidenceTimelineItem])
def get_bundle_timeline(
    bundle_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.VIEWER, UserRole.OPERATOR, UserRole.ADMIN])),
) -> List[EvidenceTimelineItem]:
    """
    Retrieve the chronological or causal sequence of evidence records within an Evidence Bundle.
    """
    records = EvidenceService.get_bundle_timeline(db, bundle_id)
    return records


@router.get("/entity/{entity_type}/{entity_id}", response_model=List[EvidenceRecordResponse])
def get_entity_evidence(
    entity_type: str,
    entity_id: str,
    domain: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.VIEWER, UserRole.OPERATOR, UserRole.ADMIN])),
) -> List[EvidenceRecordResponse]:
    """
    Retrieve all evidence records linked to a specific entity.
    """
    return EvidenceService.get_entity_evidence(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
        domain=domain,
    )


@router.get("/entity/{entity_type}/{entity_id}/timeline", response_model=List[EvidenceTimelineItem])
def get_entity_timeline(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.VIEWER, UserRole.OPERATOR, UserRole.ADMIN])),
) -> List[EvidenceTimelineItem]:
    """
    Retrieve the ordered evidence timeline for an entity.
    For C-MAPSS machines, timeline ordering strictly respects observation_cycle.
    """
    return EvidenceService.get_entity_timeline(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
    )


@router.get("/relationships/{evidence_id}", response_model=Dict[str, List[EvidenceRelationshipResponse]])
def get_evidence_relationships(
    evidence_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.VIEWER, UserRole.OPERATOR, UserRole.ADMIN])),
) -> Dict[str, List[EvidenceRelationshipResponse]]:
    """
    Retrieve incoming and outgoing causal relationships for a specific evidence record.
    """
    return EvidenceService.get_relationships(db, evidence_id)


@router.get("/provenance/{evidence_id}", response_model=EvidenceProvenanceResponse)
def get_evidence_provenance(
    evidence_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.VIEWER, UserRole.OPERATOR, UserRole.ADMIN])),
) -> EvidenceProvenanceResponse:
    """
    Retrieve provenance, checksums, and version calibration metadata for an evidence record.
    """
    prov = EvidenceService.get_provenance(db, evidence_id)
    return EvidenceProvenanceResponse(**prov)


@router.get("/{evidence_id}", response_model=EvidenceRecordResponse)
def get_evidence_record(
    evidence_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.VIEWER, UserRole.OPERATOR, UserRole.ADMIN])),
) -> EvidenceRecordResponse:
    """
    Retrieve an individual evidence record by UUID.
    """
    return EvidenceService.get_evidence(db, evidence_id)
