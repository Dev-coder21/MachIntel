from datetime import datetime, timezone
import logging
import os
from pathlib import Path
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_current_user_with_query_token, get_db
from backend.app.models.inspection import InspectionResult, InspectionRun
from backend.app.models.user import User, UserRole
from backend.app.schemas.inspection import (
    InspectionResultResponse,
    InspectionRunCreate,
    InspectionRunResponse,
    InspectionRunSummaryResponse,
)
from backend.app.services.cv_model_service import (
    DEFAULT_DATASET_DIR,
    DEFAULT_INSPECTION_STORAGE_DIR,
    DEFAULT_MODEL_DIR,
    MODEL_VERSION,
    PROJECT_ROOT,
    PatchCoreDetector,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Visual Inspection (Computer Vision)"])


def _validate_safe_path(file_path: Optional[str], allowed_roots: List[Path]) -> Path:
    """
    Prevents path traversal attacks by resolving path and asserting it resides
    strictly within the allowed base directories.
    """
    if not file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact path not specified.")

    resolved = Path(file_path).resolve()
    is_safe = any(
        resolved == root.resolve() or root.resolve() in resolved.parents
        for root in allowed_roots
    )

    if not is_safe:
        logger.warning(f"Path traversal attempt blocked: {file_path}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to path outside permitted directories is forbidden.",
        )

    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact file not found.")

    return resolved


@router.get(
    "/inspections",
    response_model=List[InspectionRunResponse],
    summary="List visual inspection runs",
)
def list_inspections(
    category: Optional[str] = Query(None, description="Filter by category (e.g. metal_nut)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[InspectionRunResponse]:
    stmt = select(InspectionRun)
    if category:
        stmt = stmt.where(InspectionRun.category == category)
    if status_filter:
        stmt = stmt.where(InspectionRun.status == status_filter)

    stmt = stmt.order_by(desc(InspectionRun.created_at)).offset(offset).limit(limit)
    runs = db.execute(stmt).scalars().all()
    return [InspectionRunResponse.model_validate(r) for r in runs]


@router.get(
    "/inspections/{inspection_id}",
    response_model=InspectionRunResponse,
    summary="Get visual inspection run details",
)
def get_inspection(
    inspection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InspectionRunResponse:
    run = db.get(InspectionRun, inspection_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection run not found.")
    return InspectionRunResponse.model_validate(run)


@router.get(
    "/inspections/{inspection_id}/summary",
    response_model=InspectionRunSummaryResponse,
    summary="Get inspection run evaluation summary and defect breakdown",
)
def get_inspection_summary(
    inspection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InspectionRunSummaryResponse:
    run = db.get(InspectionRun, inspection_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection run not found.")

    summary = run.evaluation_summary or {}
    defect_rate = (run.defect_count / run.total_images) if run.total_images > 0 else 0.0

    return InspectionRunSummaryResponse(
        run_id=run.id,
        dataset_identifier=run.dataset_identifier,
        category=run.category,
        model_version=run.model_version,
        policy_version=run.policy_version,
        threshold=run.threshold,
        total_images=run.total_images,
        passed_count=run.passed_count,
        defect_count=run.defect_count,
        defect_rate=round(defect_rate, 4),
        metrics=summary.get("image_level_metrics", {}),
        defect_breakdown=summary.get("defect_breakdown", {}),
    )


@router.get(
    "/inspections/{inspection_id}/results",
    response_model=List[InspectionResultResponse],
    summary="Get visual inspection results for a run",
)
def get_inspection_results(
    inspection_id: uuid.UUID,
    defect_class: Optional[str] = Query(None, description="Filter by defect class (bent, color, flip, scratch, good)"),
    decision: Optional[str] = Query(None, description="Filter by decision (PASS, DEFECT)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[InspectionResultResponse]:
    run = db.get(InspectionRun, inspection_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection run not found.")

    stmt = select(InspectionResult).where(InspectionResult.run_id == inspection_id)
    if defect_class:
        stmt = stmt.where(InspectionResult.defect_class == defect_class)
    if decision:
        stmt = stmt.where(InspectionResult.decision == decision)

    stmt = stmt.order_by(InspectionResult.source_image_filename).offset(offset).limit(limit)
    results = db.execute(stmt).scalars().all()

    response_items = []
    for r in results:
        item = InspectionResultResponse(
            id=r.id,
            run_id=r.run_id,
            split=r.split,
            defect_class=r.defect_class,
            source_image_filename=r.source_image_filename,
            image_level_score=r.image_level_score,
            decision=r.decision,
            ground_truth_label=r.ground_truth_label,
            has_heatmap=bool(r.heatmap_path and Path(r.heatmap_path).exists()),
            has_overlay=bool(r.overlay_path and Path(r.overlay_path).exists()),
            has_ground_truth_mask=bool(r.ground_truth_mask_path and Path(r.ground_truth_mask_path).exists()),
            inference_metadata=r.inference_metadata or {},
            created_at=r.created_at,
        )
        response_items.append(item)

    return response_items


@router.post(
    "/inspections/run",
    response_model=InspectionRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger visual inspection evaluation run (Admin/Operator only)",
)
def run_inspection(
    payload: Optional[InspectionRunCreate] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InspectionRunResponse:
    if current_user.role not in [UserRole.ADMIN, UserRole.OPERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Operator or Admin role required to run inspection.",
        )

    category = payload.category if payload else "metal_nut"
    if category != "metal_nut":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category '{category}' not supported in Phase 6. Only 'metal_nut' is active.",
        )

    # Resolve active visual inspection model through model registry
    from backend.app.services.model_lifecycle_service import ModelLifecycleService, safe_resolve_artifact_path
    from backend.app.models.model_registry import ModelDomain

    active_model = ModelLifecycleService.get_active_model(db, domain=ModelDomain.VISUAL_INSPECTION.value)
    model_dir = safe_resolve_artifact_path(active_model.artifact_path)

    detector = PatchCoreDetector(model_version=active_model.model_id)
    if not (model_dir / "memory_bank.pt").exists():
        detector.build_memory_bank(train_good_dir=DEFAULT_DATASET_DIR / "train" / "good", subsample_ratio=0.05, seed=42)
        detector.save_model(model_dir=model_dir)
    else:
        detector.load_model(model_dir=model_dir)

    run_id = uuid.uuid4()
    eval_summary, results_data = detector.evaluate_dataset(
        dataset_dir=DEFAULT_DATASET_DIR,
        run_id=str(run_id),
        storage_dir=DEFAULT_INSPECTION_STORAGE_DIR,
    )

    run_record = InspectionRun(
        id=run_id,
        dataset_identifier=eval_summary["dataset_identifier"],
        category=eval_summary["category"],
        model_version=eval_summary["model_version"],
        feature_config_version=eval_summary["feature_config_version"],
        policy_version=eval_summary["policy_version"],
        status="COMPLETED",
        threshold=eval_summary["threshold"],
        total_images=eval_summary["total_images_evaluated"],
        passed_count=eval_summary["passed_count"],
        defect_count=eval_summary["defect_count"],
        evaluation_summary=eval_summary,
        created_at=datetime.now(timezone.utc),
    )
    db.add(run_record)
    db.flush()

    for res in results_data:
        res_record = InspectionResult(
            id=uuid.UUID(res["id"]),
            run_id=run_id,
            split=res["split"],
            defect_class=res["defect_class"],
            source_image_path=res["source_image_path"],
            source_image_filename=res["source_image_filename"],
            image_level_score=res["image_level_score"],
            decision=res["decision"],
            ground_truth_label=res["ground_truth_label"],
            heatmap_path=res["heatmap_path"],
            overlay_path=res["overlay_path"],
            ground_truth_mask_path=res["ground_truth_mask_path"],
            inference_metadata=res["inference_metadata"],
            created_at=res["created_at"],
        )
        db.add(res_record)

    db.commit()
    db.refresh(run_record)
    return InspectionRunResponse.model_validate(run_record)


@router.get(
    "/inspections/results/{result_id}",
    response_model=InspectionResultResponse,
    summary="Get single inspection result details",
)
def get_inspection_result(
    result_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InspectionResultResponse:
    res = db.get(InspectionResult, result_id)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection result not found.")

    return InspectionResultResponse(
        id=res.id,
        run_id=res.run_id,
        split=res.split,
        defect_class=res.defect_class,
        source_image_filename=res.source_image_filename,
        image_level_score=res.image_level_score,
        decision=res.decision,
        ground_truth_label=res.ground_truth_label,
        has_heatmap=bool(res.heatmap_path and Path(res.heatmap_path).exists()),
        has_overlay=bool(res.overlay_path and Path(res.overlay_path).exists()),
        has_ground_truth_mask=bool(res.ground_truth_mask_path and Path(res.ground_truth_mask_path).exists()),
        inference_metadata=res.inference_metadata or {},
        created_at=res.created_at,
    )


# --- Safe Artifact Streaming Endpoints with Path Traversal Protection ---

ALLOWED_STORAGE_ROOTS = [
    PROJECT_ROOT / "storage" / "inspections",
    PROJECT_ROOT / "data" / "raw" / "mvtec_ad",
]


@router.get(
    "/inspections/results/{result_id}/heatmap",
    summary="Stream pixel-level anomaly heatmap PNG",
)
def get_result_heatmap(
    result_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_query_token),
):
    res = db.get(InspectionResult, result_id)
    if not res or not res.heatmap_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Heatmap artifact not found.")

    safe_path = _validate_safe_path(res.heatmap_path, ALLOWED_STORAGE_ROOTS)
    return FileResponse(safe_path, media_type="image/png")


@router.get(
    "/inspections/results/{result_id}/overlay",
    summary="Stream visualization overlay PNG",
)
def get_result_overlay(
    result_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_query_token),
):
    res = db.get(InspectionResult, result_id)
    if not res or not res.overlay_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Overlay artifact not found.")

    safe_path = _validate_safe_path(res.overlay_path, ALLOWED_STORAGE_ROOTS)
    return FileResponse(safe_path, media_type="image/png")


@router.get(
    "/inspections/results/{result_id}/original",
    summary="Stream original raw image PNG",
)
def get_result_original(
    result_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_query_token),
):
    res = db.get(InspectionResult, result_id)
    if not res or not res.source_image_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source image not found.")

    safe_path = _validate_safe_path(res.source_image_path, ALLOWED_STORAGE_ROOTS)
    return FileResponse(safe_path, media_type="image/png")


@router.get(
    "/inspections/results/{result_id}/mask",
    summary="Stream ground truth mask PNG (evaluation only)",
)
def get_result_mask(
    result_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_with_query_token),
):
    res = db.get(InspectionResult, result_id)
    if not res or not res.ground_truth_mask_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ground truth mask not found.")

    safe_path = _validate_safe_path(res.ground_truth_mask_path, ALLOWED_STORAGE_ROOTS)
    return FileResponse(safe_path, media_type="image/png")
