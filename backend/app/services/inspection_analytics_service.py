from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import HTTPException, status
import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.models.inspection import InspectionResult, InspectionRun
from backend.app.schemas.inspection_analytics import (
    ConfusionMatrixAnalyticsResponse,
    DefectClassAnalyticsItem,
    DefectClassAnalyticsResponse,
    InspectionRunAnalyticsSummaryResponse,
    InspectionRunProvenanceResponse,
    LocalizationAnalyticsResponse,
    RunComparisonItem,
    RunComparisonResponse,
    ScoreDistributionResponse,
    ScoreHistogramBin,
)

logger = logging.getLogger(__name__)


class InspectionAnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def _get_run(self, run_id: uuid.UUID) -> InspectionRun:
        run = self.db.get(InspectionRun, run_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inspection run '{run_id}' not found.",
            )
        return run

    def list_runs(
        self,
        dataset_identifier: Optional[str] = None,
        model_version: Optional[str] = None,
        policy_version: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[InspectionRun]:
        stmt = select(InspectionRun)
        if dataset_identifier:
            stmt = stmt.where(InspectionRun.dataset_identifier == dataset_identifier)
        if model_version:
            stmt = stmt.where(InspectionRun.model_version == model_version)
        if policy_version:
            stmt = stmt.where(InspectionRun.policy_version == policy_version)
        if status_filter:
            stmt = stmt.where(InspectionRun.status == status_filter)

        stmt = stmt.order_by(desc(InspectionRun.created_at)).offset(offset).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def get_run_summary(self, run_id: uuid.UUID) -> InspectionRunAnalyticsSummaryResponse:
        run = self._get_run(run_id)
        results = self.db.query(InspectionResult).filter(InspectionResult.run_id == run_id).all()

        if results:
            scores = [r.image_level_score for r in results]
            score_min = float(np.min(scores))
            score_max = float(np.max(scores))
            score_mean = float(np.mean(scores))
            score_median = float(np.median(scores))
        else:
            score_min = score_max = score_mean = score_median = 0.0

        defect_rate = (run.defect_count / run.total_images) if run.total_images > 0 else 0.0
        eval_metrics = (run.evaluation_summary or {}).get("image_level_metrics", {})

        return InspectionRunAnalyticsSummaryResponse(
            run_id=run.id,
            dataset_identifier=run.dataset_identifier,
            category=run.category,
            model_version=run.model_version,
            feature_config_version=run.feature_config_version,
            policy_version=run.policy_version,
            status=run.status,
            threshold=round(run.threshold, 4),
            total_images=run.total_images,
            passed_count=run.passed_count,
            defect_count=run.defect_count,
            observed_defect_rate=round(defect_rate, 4),
            score_min=round(score_min, 4),
            score_max=round(score_max, 4),
            score_mean=round(score_mean, 4),
            score_median=round(score_median, 4),
            evaluation_metrics=eval_metrics,
            created_at=run.created_at,
        )

    def get_score_distribution(
        self,
        run_id: uuid.UUID,
        num_bins: int = 15,
    ) -> ScoreDistributionResponse:
        run = self._get_run(run_id)
        results = self.db.query(InspectionResult).filter(InspectionResult.run_id == run_id).all()

        if not results:
            return ScoreDistributionResponse(
                run_id=run.id,
                threshold=round(run.threshold, 4),
                overall_stats={},
                normal_stats={},
                defective_stats={},
                histogram=[],
            )

        all_scores = np.array([r.image_level_score for r in results])
        normal_scores = np.array([r.image_level_score for r in results if r.ground_truth_label == "PASS"])
        defective_scores = np.array([r.image_level_score for r in results if r.ground_truth_label == "DEFECT"])

        def calc_stats(arr: np.ndarray) -> Dict[str, float]:
            if len(arr) == 0:
                return {}
            return {
                "count": float(len(arr)),
                "min": round(float(np.min(arr)), 4),
                "max": round(float(np.max(arr)), 4),
                "mean": round(float(np.mean(arr)), 4),
                "median": round(float(np.median(arr)), 4),
                "std": round(float(np.std(arr)), 4),
                "p5": round(float(np.percentile(arr, 5)), 4),
                "p25": round(float(np.percentile(arr, 25)), 4),
                "p75": round(float(np.percentile(arr, 75)), 4),
                "p95": round(float(np.percentile(arr, 95)), 4),
            }

        overall_stats = calc_stats(all_scores)
        norm_stats = calc_stats(normal_scores)
        defect_stats = calc_stats(defective_scores)

        # Build histogram spanning the overall range
        s_min, s_max = float(np.min(all_scores)), float(np.max(all_scores))
        bin_edges = np.linspace(s_min, s_max, num_bins + 1)

        histogram: List[ScoreHistogramBin] = []
        for i in range(num_bins):
            b_start = float(bin_edges[i])
            b_end = float(bin_edges[i + 1])

            # In the last bin, include the upper edge
            if i == num_bins - 1:
                n_mask = (normal_scores >= b_start) & (normal_scores <= b_end) if len(normal_scores) else []
                d_mask = (defective_scores >= b_start) & (defective_scores <= b_end) if len(defective_scores) else []
            else:
                n_mask = (normal_scores >= b_start) & (normal_scores < b_end) if len(normal_scores) else []
                d_mask = (defective_scores >= b_start) & (defective_scores < b_end) if len(defective_scores) else []

            n_cnt = int(np.sum(n_mask))
            d_cnt = int(np.sum(d_mask))
            histogram.append(
                ScoreHistogramBin(
                    bin_start=round(b_start, 4),
                    bin_end=round(b_end, 4),
                    normal_count=n_cnt,
                    defect_count=d_cnt,
                    total_count=n_cnt + d_cnt,
                )
            )

        return ScoreDistributionResponse(
            run_id=run.id,
            threshold=round(run.threshold, 4),
            overall_stats=overall_stats,
            normal_stats=norm_stats,
            defective_stats=defect_stats,
            histogram=histogram,
        )

    def get_defect_class_analytics(self, run_id: uuid.UUID) -> DefectClassAnalyticsResponse:
        run = self._get_run(run_id)
        results = self.db.query(InspectionResult).filter(InspectionResult.run_id == run_id).all()

        classes_map: Dict[str, List[InspectionResult]] = {}
        for r in results:
            classes_map.setdefault(r.defect_class, []).append(r)

        class_items: List[DefectClassAnalyticsItem] = []
        for cls_name in sorted(classes_map.keys()):
            cls_results = classes_map[cls_name]
            scores = [r.image_level_score for r in cls_results]
            img_count = len(cls_results)

            if cls_name == "good":
                # For normal images, detected normal means decision == "PASS"
                detected_count = sum(1 for r in cls_results if r.decision == "PASS")
                missed_count = sum(1 for r in cls_results if r.decision == "DEFECT")  # false alarms
            else:
                # For defect classes, detected defect means decision == "DEFECT"
                detected_count = sum(1 for r in cls_results if r.decision == "DEFECT")
                missed_count = sum(1 for r in cls_results if r.decision == "PASS")    # missed defects

            det_rate = (detected_count / img_count) if img_count > 0 else 0.0

            class_items.append(
                DefectClassAnalyticsItem(
                    defect_class=cls_name,
                    image_count=img_count,
                    detected_count=detected_count,
                    missed_count=missed_count,
                    observed_detection_rate=round(det_rate, 4),
                    mean_score=round(float(np.mean(scores)), 4) if scores else 0.0,
                    min_score=round(float(np.min(scores)), 4) if scores else 0.0,
                    max_score=round(float(np.max(scores)), 4) if scores else 0.0,
                )
            )

        return DefectClassAnalyticsResponse(
            run_id=run.id,
            category=run.category,
            classes=class_items,
        )

    def get_confusion_matrix_analytics(self, run_id: uuid.UUID) -> ConfusionMatrixAnalyticsResponse:
        run = self._get_run(run_id)
        results = self.db.query(InspectionResult).filter(InspectionResult.run_id == run_id).all()

        tp = sum(1 for r in results if r.ground_truth_label == "DEFECT" and r.decision == "DEFECT")
        tn = sum(1 for r in results if r.ground_truth_label == "PASS" and r.decision == "PASS")
        fp = sum(1 for r in results if r.ground_truth_label == "PASS" and r.decision == "DEFECT")
        fn = sum(1 for r in results if r.ground_truth_label == "DEFECT" and r.decision == "PASS")

        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        specificity = (tn / (tn + fp)) if (tn + fp) > 0 else 0.0

        # AUC calculations from actual results
        y_true = [1 if r.ground_truth_label == "DEFECT" else 0 for r in results]
        y_scores = [r.image_level_score for r in results]

        roc_auc = None
        pr_auc = None
        if len(set(y_true)) > 1:
            try:
                roc_auc = float(roc_auc_score(y_true, y_scores))
                pr_auc = float(average_precision_score(y_true, y_scores))
            except Exception as e:
                logger.warning(f"Could not compute AUC in confusion matrix: {e}")

        return ConfusionMatrixAnalyticsResponse(
            run_id=run.id,
            true_positives=tp,
            true_negatives=tn,
            false_positives=fp,
            false_negatives=fn,
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1, 4),
            specificity=round(specificity, 4),
            image_roc_auc=round(roc_auc, 4) if roc_auc is not None else None,
            image_pr_auc=round(pr_auc, 4) if pr_auc is not None else None,
            threshold=round(run.threshold, 4),
        )

    def get_localization_analytics(self, run_id: uuid.UUID) -> LocalizationAnalyticsResponse:
        run = self._get_run(run_id)
        summary = run.evaluation_summary or {}
        px_metrics = summary.get("pixel_level_metrics", {})
        px_auc = px_metrics.get("pixel_roc_auc")
        masks_count = px_metrics.get("mask_evaluated_images", 0)

        return LocalizationAnalyticsResponse(
            run_id=run.id,
            pixel_roc_auc=round(px_auc, 4) if px_auc is not None else None,
            mask_evaluated_images=masks_count,
            has_localization=bool(px_auc is not None and masks_count > 0),
            localization_method="PatchCore Euclidean Distance Map (28x28 Bilinear Upsample -> 224x224, Gaussian Filter sigma=4.0)",
            resolution="224x224 (Resized / Cropped Input)",
        )

    def get_run_provenance(self, run_id: uuid.UUID) -> InspectionRunProvenanceResponse:
        run = self._get_run(run_id)
        summary = run.evaluation_summary or {}
        normal_stats = summary.get("normal_stats", {})

        return InspectionRunProvenanceResponse(
            run_id=run.id,
            dataset_identifier=run.dataset_identifier,
            category=run.category,
            model_version=run.model_version,
            feature_config_version=run.feature_config_version,
            policy_version=run.policy_version,
            threshold=round(run.threshold, 4),
            normal_training_stats=normal_stats,
            created_at=run.created_at,
        )

    def compare_runs(self) -> RunComparisonResponse:
        runs = self.db.query(InspectionRun).order_by(desc(InspectionRun.created_at)).all()
        total_runs = len(runs)

        items: List[RunComparisonItem] = []
        for r in runs:
            summary = r.evaluation_summary or {}
            img_metrics = summary.get("image_level_metrics", {})
            px_metrics = summary.get("pixel_level_metrics", {})
            defect_rate = (r.defect_count / r.total_images) if r.total_images > 0 else 0.0

            items.append(
                RunComparisonItem(
                    run_id=r.id,
                    model_version=r.model_version,
                    policy_version=r.policy_version,
                    threshold=round(r.threshold, 4),
                    total_images=r.total_images,
                    passed_count=r.passed_count,
                    defect_count=r.defect_count,
                    observed_defect_rate=round(defect_rate, 4),
                    roc_auc=img_metrics.get("roc_auc"),
                    pr_auc=img_metrics.get("pr_auc"),
                    precision=img_metrics.get("precision"),
                    recall=img_metrics.get("recall"),
                    f1_score=img_metrics.get("f1_score"),
                    pixel_roc_auc=px_metrics.get("pixel_roc_auc"),
                    created_at=r.created_at,
                )
            )

        if total_runs < 2:
            return RunComparisonResponse(
                is_available=False,
                reason="Cross-model comparison requires at least two distinct inspection runs or configurations. Only 1 run is currently persisted.",
                total_runs=total_runs,
                runs=items,
            )

        return RunComparisonResponse(
            is_available=True,
            reason=None,
            total_runs=total_runs,
            runs=items,
        )
