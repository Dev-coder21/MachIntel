#!/usr/bin/env python3
"""
Full Evaluation & Inspection Run Persistence for MVTec AD metal_nut.
Evaluates official test split (115 images: 22 good, 25 bent, 22 color, 23 flip, 23 scratch),
computes image-level & pixel-level metrics, and records results into PostgreSQL.

Usage:
    python backend/scripts/evaluate_cv_metalnut.py
"""

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
import uuid

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.db.session import SessionLocal
from backend.app.models.inspection import InspectionResult, InspectionRun
from backend.app.services.cv_model_service import (
    DEFAULT_DATASET_DIR,
    DEFAULT_INSPECTION_STORAGE_DIR,
    DEFAULT_MODEL_DIR,
    MODEL_VERSION,
    PatchCoreDetector,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_cv_metalnut")


def evaluate_and_persist(
    dataset_dir: Path = DEFAULT_DATASET_DIR,
    model_dir: Path = DEFAULT_MODEL_DIR,
    storage_dir: Path = DEFAULT_INSPECTION_STORAGE_DIR,
) -> InspectionRun:
    detector = PatchCoreDetector(model_version=MODEL_VERSION)

    # Check if model is already built, otherwise build it
    if not (model_dir / "memory_bank.pt").exists() or not (model_dir / "config.json").exists():
        logger.info(f"Model artifacts not found in {model_dir}. Building memory bank first...")
        train_good = dataset_dir / "train" / "good"
        detector.build_memory_bank(train_good_dir=train_good, subsample_ratio=0.05, seed=42)
        detector.save_model(model_dir=model_dir)
    else:
        detector.load_model(model_dir=model_dir)

    run_id = uuid.uuid4()
    logger.info(f"=== Initiating Official Evaluation Run [{run_id}] ===")
    logger.info(f"Dataset: MVTec AD (metal_nut)")
    logger.info(f"Model Version: {detector.model_version}")
    logger.info(f"Calibrated Threshold: {detector.threshold:.4f}")

    eval_summary, results_data = detector.evaluate_dataset(
        dataset_dir=dataset_dir,
        run_id=str(run_id),
        storage_dir=storage_dir,
    )

    logger.info(f"Saving InspectionRun and {len(results_data)} InspectionResults to PostgreSQL...")

    db = SessionLocal()
    try:
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
            result_record = InspectionResult(
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
            db.add(result_record)

        db.commit()
        logger.info(f"Database commit successful. Run ID: {run_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error persisting inspection run to database: {e}")
        raise
    finally:
        db.close()

    # Log summary report
    img_metrics = eval_summary["image_level_metrics"]
    px_metrics = eval_summary["pixel_level_metrics"]
    breakdown = eval_summary["defect_breakdown"]

    logger.info("==================================================")
    logger.info("             MVTEC METAL_NUT EVALUATION           ")
    logger.info("==================================================")
    logger.info(f"Run ID:            {run_id}")
    logger.info(f"Total Evaluated:   {eval_summary['total_images_evaluated']}")
    logger.info(f"Model Threshold:   {eval_summary['threshold']}")
    logger.info(f"Image ROC-AUC:     {img_metrics['roc_auc']:.4f}")
    logger.info(f"Image PR-AUC:      {img_metrics['pr_auc']:.4f}")
    logger.info(f"Image F1-Score:    {img_metrics['f1_score']:.4f}")
    logger.info(f"Precision:         {img_metrics['precision']:.4f}")
    logger.info(f"Recall:            {img_metrics['recall']:.4f}")
    if px_metrics.get("pixel_roc_auc") is not None:
        logger.info(f"Pixel ROC-AUC:     {px_metrics['pixel_roc_auc']:.4f}")
    logger.info("--------------------------------------------------")
    logger.info("Category Breakdown:")
    for cls_name, cls_info in breakdown.items():
        logger.info(
            f"  {cls_name.upper():<8}: Total={cls_info['total_images']:2d} | "
            f"Pass={cls_info['passed_count']:2d} | Defect={cls_info['defect_count']:2d} | "
            f"Accuracy={cls_info['accuracy']*100:.1f}% | "
            f"Score(Mean/Min/Max)={cls_info['mean_score']:.2f}/{cls_info['min_score']:.2f}/{cls_info['max_score']:.2f}"
        )
    logger.info("==================================================")

    return run_record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run evaluation on MVTec metal_nut and persist to DB")
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--storage-dir", type=Path, default=DEFAULT_INSPECTION_STORAGE_DIR)
    args = parser.parse_args()

    evaluate_and_persist(
        dataset_dir=args.dataset_dir,
        model_dir=args.model_dir,
        storage_dir=args.storage_dir,
    )
