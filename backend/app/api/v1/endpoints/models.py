from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db, require_roles
from backend.app.models.model_registry import (
    ModelDomain,
    ModelEvaluation,
    ModelLifecycleStatus,
    ModelPromotion,
    ModelRegistry,
)
from backend.app.models.user import User, UserRole
from backend.app.schemas.model import (
    ModelEvaluationResponse,
    ModelGateEvaluationReport,
    ModelIntegrityResponse,
    ModelMonitoringSummary,
    ModelPromotionRequest,
    ModelPromotionResponse,
    ModelRegistrationRequest,
    ModelRegistryListResponse,
    ModelRegistryResponse,
)
from backend.app.services.model_lifecycle_service import (
    ModelLifecycleService,
    get_artifact_directory_details,
    safe_resolve_artifact_path,
)

router = APIRouter(prefix="/models", tags=["Model Registry & Evaluation"])


@router.get("", response_model=ModelRegistryListResponse, summary="List registered baseline and evaluation models")
def list_models(
    domain: Optional[str] = Query(None, description="Filter by domain: MACHINE_HEALTH or VISUAL_INSPECTION"),
    model_family: Optional[str] = Query(None, description="Filter by model family: RUL_REGRESSION, ANOMALY_DETECTION"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by lifecycle status"),
    version: Optional[str] = Query(None, description="Filter by version string"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ModelRegistryListResponse:
    """Returns all registered models with their validation/test metrics, integrity status, and active deployment flags."""
    stmt = select(ModelRegistry).order_by(ModelRegistry.created_at.desc())

    if domain:
        stmt = stmt.where(ModelRegistry.domain == domain)
    if model_family:
        stmt = stmt.where(ModelRegistry.model_family == model_family)
    if status_filter:
        stmt = stmt.where(ModelRegistry.status == status_filter)
    if version:
        stmt = stmt.where(ModelRegistry.version == version)

    models = list(db.execute(stmt).scalars().all())

    # Find active models by domain
    active_rul = db.execute(
        select(ModelRegistry).where(
            ModelRegistry.domain == ModelDomain.MACHINE_HEALTH.value,
            ModelRegistry.is_active == True,
        )
    ).scalars().first()

    active_cv = db.execute(
        select(ModelRegistry).where(
            ModelRegistry.domain == ModelDomain.VISUAL_INSPECTION.value,
            ModelRegistry.is_active == True,
        )
    ).scalars().first()

    return ModelRegistryListResponse(
        total=len(models),
        active_machine_health_model_id=active_rul.model_id if active_rul else None,
        active_visual_inspection_model_id=active_cv.model_id if active_cv else None,
        active_model_id=active_rul.model_id if active_rul else (active_cv.model_id if active_cv else None),
        items=[ModelRegistryResponse.model_validate(m) for m in models],
    )


@router.get("/monitoring/summary", response_model=ModelMonitoringSummary, summary="Defensible model monitoring summary")
def get_monitoring_summary(
    domain: str = Query(ModelDomain.MACHINE_HEALTH.value, description="Domain to summarize: MACHINE_HEALTH or VISUAL_INSPECTION"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ModelMonitoringSummary:
    """Returns empirical operational inference statistics and distributions without fabricating synthetic drift."""
    summary_data = ModelLifecycleService.get_monitoring_summary(db, domain=domain)
    return ModelMonitoringSummary(**summary_data)


@router.post("/register", response_model=ModelRegistryResponse, summary="Register a new model artifact in the registry (Admin only)")
def register_model(
    payload: ModelRegistrationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
) -> ModelRegistryResponse:
    """Registers a model artifact after strictly verifying path containment and computing SHA-256 integrity."""
    existing = db.execute(
        select(ModelRegistry).where(ModelRegistry.model_id == payload.model_id)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model identifier '{payload.model_id}' is already registered in registry.",
        )

    # Validate path containment safely
    target_dir = safe_resolve_artifact_path(payload.artifact_path)
    dir_details = get_artifact_directory_details(target_dir)

    if not dir_details["exists"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Artifact directory does not exist at {payload.artifact_path}.",
        )

    # Assemble metadata
    meta = dict(payload.metadata_json)
    meta["file_checksums"] = dir_details.get("files", {})

    model = ModelRegistry(
        model_id=payload.model_id,
        model_name=payload.model_name,
        domain=payload.domain,
        model_family=payload.model_family,
        algorithm=payload.algorithm,
        task=payload.model_family,
        version=payload.version,
        status=ModelLifecycleStatus.REGISTERED.value,
        framework=payload.framework,
        dataset_identifier=payload.dataset_identifier,
        dataset_version=payload.dataset_version,
        feature_engineering_version=payload.feature_engineering_version,
        preprocessing_version="1.0.0",
        window_size=0,
        hyperparameters=payload.hyperparameters,
        metrics={},
        artifact_path=payload.artifact_path,
        artifact_sha256=dir_details.get("primary_sha256"),
        artifact_size_bytes=dir_details.get("primary_size_bytes"),
        training_manifest=payload.training_manifest,
        evaluation_manifest=payload.evaluation_manifest,
        description=payload.description,
        metadata_json=meta,
        is_active=False,
    )
    db.add(model)
    db.commit()
    db.refresh(model)

    return ModelRegistryResponse.model_validate(model)


@router.get("/{model_id}", response_model=ModelRegistryResponse, summary="Get details and metrics for a specific model")
def get_model(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ModelRegistryResponse:
    """Returns full metadata, hyperparameters, feature importances, and evaluation metrics for a specific model version."""
    model = db.execute(
        select(ModelRegistry).where(ModelRegistry.model_id == model_id)
    ).scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model with identifier '{model_id}' was not found in registry.",
        )

    return ModelRegistryResponse.model_validate(model)


@router.get("/{model_id}/integrity", response_model=ModelIntegrityResponse, summary="Verify model artifact cryptographic integrity")
def get_model_integrity(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ModelIntegrityResponse:
    """Cryptographically verifies that artifact files exist and match recorded SHA-256 digests."""
    model = db.execute(
        select(ModelRegistry).where(ModelRegistry.model_id == model_id)
    ).scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' was not found in registry.",
        )

    integrity_report = ModelLifecycleService.verify_artifact_integrity(model)
    return ModelIntegrityResponse(**integrity_report)


@router.post("/{model_id}/verify-integrity", response_model=ModelIntegrityResponse, summary="Trigger on-demand integrity verification")
def trigger_verify_integrity(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ModelIntegrityResponse:
    """On-demand verification action updating verification timestamp and checking disk integrity."""
    model = db.execute(
        select(ModelRegistry).where(ModelRegistry.model_id == model_id)
    ).scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' was not found in registry.",
        )

    integrity_report = ModelLifecycleService.verify_artifact_integrity(model)
    return ModelIntegrityResponse(**integrity_report)


@router.get("/{model_id}/gates", response_model=ModelGateEvaluationReport, summary="Evaluate promotion gates for a model")
def get_promotion_gates(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ModelGateEvaluationReport:
    """Evaluates all 8 deterministic promotion gates without modifying model state."""
    model = db.execute(
        select(ModelRegistry).where(ModelRegistry.model_id == model_id)
    ).scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' was not found in registry.",
        )

    can_promote, report = ModelLifecycleService.evaluate_promotion_gates(db, model)
    return ModelGateEvaluationReport(**report)


@router.get("/{model_id}/evaluations", response_model=List[ModelEvaluationResponse], summary="List evaluation history for a model")
def get_model_evaluations(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ModelEvaluationResponse]:
    """Returns immutable evaluation records with metrics, manifests, and gate results."""
    model = db.execute(
        select(ModelRegistry).where(ModelRegistry.model_id == model_id)
    ).scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' was not found in registry.",
        )

    evals = list(
        db.execute(
            select(ModelEvaluation)
            .where(ModelEvaluation.model_version_id == model.id)
            .order_by(desc(ModelEvaluation.evaluated_at))
        ).scalars().all()
    )

    return [ModelEvaluationResponse.model_validate(e) for e in evals]


@router.get("/{model_id}/promotions", response_model=List[ModelPromotionResponse], summary="List promotion audit log for a model")
def get_model_promotions(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ModelPromotionResponse]:
    """Returns the immutable audit log of promotions and lifecycle transitions for this model."""
    model = db.execute(
        select(ModelRegistry).where(ModelRegistry.model_id == model_id)
    ).scalar_one_or_none()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' was not found in registry.",
        )

    promotions = list(
        db.execute(
            select(ModelPromotion)
            .where(ModelPromotion.model_version_id == model.id)
            .order_by(desc(ModelPromotion.promoted_at))
        ).scalars().all()
    )

    return [ModelPromotionResponse.model_validate(p) for p in promotions]


@router.post("/{model_id}/promote", response_model=ModelRegistryResponse, summary="Promote model to active production status (Admin only)")
def promote_model(
    model_id: str,
    payload: ModelPromotionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
) -> ModelRegistryResponse:
    """Enforces deterministic promotion gates, transitions existing model to RETIRED, and promotes target model."""
    promoted_model = ModelLifecycleService.promote_model(
        db=db,
        model_id=model_id,
        reason=payload.reason,
        promoted_by=current_user,
    )
    return ModelRegistryResponse.model_validate(promoted_model)


@router.post("/{model_id}/retire", response_model=ModelRegistryResponse, summary="Retire a model from active production status (Admin only)")
def retire_model(
    model_id: str,
    payload: ModelPromotionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
) -> ModelRegistryResponse:
    """Demotes model to RETIRED status, logging audit reason."""
    retired_model = ModelLifecycleService.retire_model(
        db=db,
        model_id=model_id,
        reason=payload.reason,
        retired_by=current_user,
    )
    return ModelRegistryResponse.model_validate(retired_model)
