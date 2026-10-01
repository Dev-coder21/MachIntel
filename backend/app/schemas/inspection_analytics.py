from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ScoreHistogramBin(BaseModel):
    bin_start: float
    bin_end: float
    normal_count: int
    defect_count: int
    total_count: int


class ScoreDistributionResponse(BaseModel):
    run_id: uuid.UUID
    threshold: float
    overall_stats: Dict[str, float]
    normal_stats: Dict[str, float]
    defective_stats: Dict[str, float]
    histogram: List[ScoreHistogramBin]


class DefectClassAnalyticsItem(BaseModel):
    defect_class: str
    image_count: int
    detected_count: int
    missed_count: int
    observed_detection_rate: float
    mean_score: float
    min_score: float
    max_score: float


class DefectClassAnalyticsResponse(BaseModel):
    run_id: uuid.UUID
    category: str
    classes: List[DefectClassAnalyticsItem]


class ConfusionMatrixAnalyticsResponse(BaseModel):
    run_id: uuid.UUID
    true_positives: int
    true_negatives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    specificity: float
    image_roc_auc: Optional[float] = None
    image_pr_auc: Optional[float] = None
    threshold: float


class LocalizationAnalyticsResponse(BaseModel):
    run_id: uuid.UUID
    pixel_roc_auc: Optional[float] = None
    mask_evaluated_images: int
    has_localization: bool
    localization_method: str
    resolution: str


class InspectionRunProvenanceResponse(BaseModel):
    run_id: uuid.UUID
    dataset_identifier: str
    category: str
    model_version: str
    feature_config_version: str
    policy_version: str
    threshold: float
    normal_training_stats: Dict[str, Any]
    created_at: datetime


class RunComparisonItem(BaseModel):
    run_id: uuid.UUID
    model_version: str
    policy_version: str
    threshold: float
    total_images: int
    passed_count: int
    defect_count: int
    observed_defect_rate: float
    roc_auc: Optional[float] = None
    pr_auc: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    pixel_roc_auc: Optional[float] = None
    created_at: datetime


class RunComparisonResponse(BaseModel):
    is_available: bool
    reason: Optional[str] = None
    total_runs: int
    runs: List[RunComparisonItem]


class InspectionRunAnalyticsSummaryResponse(BaseModel):
    run_id: uuid.UUID
    dataset_identifier: str
    category: str
    model_version: str
    feature_config_version: str
    policy_version: str
    status: str
    threshold: float
    total_images: int
    passed_count: int
    defect_count: int
    observed_defect_rate: float
    score_min: float
    score_max: float
    score_mean: float
    score_median: float
    evaluation_metrics: Dict[str, Any]
    created_at: datetime
