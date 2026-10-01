import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ModelMetrics(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    val_rmse: Optional[float] = Field(None, description="Root Mean Squared Error on validation engines")
    val_phm_score: Optional[float] = Field(None, description="NASA/PHM 2008 asymmetric penalty score on validation engines")
    test_rmse: Optional[float] = Field(None, description="Root Mean Squared Error on official test engines")
    test_phm_score: Optional[float] = Field(None, description="NASA/PHM 2008 asymmetric penalty score on official test engines")
    roc_auc: Optional[float] = Field(None, description="Image-level ROC-AUC for anomaly detection")
    pr_auc: Optional[float] = Field(None, description="Image-level PR-AUC for anomaly detection")
    precision: Optional[float] = Field(None, description="Precision score")
    recall: Optional[float] = Field(None, description="Recall score")
    f1_score: Optional[float] = Field(None, description="F1 score")
    pixel_roc_auc: Optional[float] = Field(None, description="Pixel-level ROC-AUC score")
    train_samples: Optional[int] = Field(None, description="Number of training samples/images")
    val_samples: Optional[int] = Field(None, description="Number of validation samples/images")
    test_samples: Optional[int] = Field(None, description="Number of test samples/images evaluated")


class ModelEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    model_version_id: uuid.UUID
    evaluation_type: str
    dataset_identifier: str
    split: str
    metrics: Dict[str, Any]
    manifest: Dict[str, Any]
    gate_result: str
    gate_details: Dict[str, Any]
    evaluator: str
    evaluated_at: datetime
    created_at: datetime


class ModelPromotionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    model_version_id: uuid.UUID
    from_status: str
    to_status: str
    promoted_by_id: Optional[uuid.UUID] = None
    reason: str
    promotion_policy_version: str
    gate_results: Dict[str, Any]
    promoted_at: datetime
    created_at: datetime


class ModelRegistryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    model_id: str
    model_name: str
    domain: str
    model_family: str
    algorithm: str
    task: str
    version: str
    status: str
    framework: str
    dataset_identifier: str
    dataset_version: Optional[str] = None
    feature_engineering_version: str
    feature_version: Optional[str] = None
    preprocessing_version: str
    window_size: int
    hyperparameters: Dict[str, Any]
    metrics: Dict[str, Any]
    feature_names: Optional[List[str]] = None
    feature_importances: Optional[Dict[str, float]] = None
    artifact_path: str
    artifact_sha256: Optional[str] = None
    artifact_size_bytes: Optional[int] = None
    training_manifest: Dict[str, Any] = Field(default_factory=dict)
    evaluation_manifest: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    parent_model_id: Optional[str] = None
    is_active: bool
    registered_at: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None


class ModelRegistryListResponse(BaseModel):
    total: int
    active_machine_health_model_id: Optional[str] = None
    active_visual_inspection_model_id: Optional[str] = None
    # For backward compatibility with existing tests/APIs
    active_model_id: Optional[str] = None
    items: List[ModelRegistryResponse]


class ModelPromotionRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500, description="Mandatory audit explanation for promotion/demotion")


class ModelRegistrationRequest(BaseModel):
    model_id: str = Field(..., min_length=3, max_length=100)
    model_name: str = Field(..., min_length=3, max_length=100)
    domain: str = Field(..., description="MACHINE_HEALTH or VISUAL_INSPECTION")
    model_family: str = Field(..., description="e.g. RUL_REGRESSION or ANOMALY_DETECTION")
    algorithm: str
    version: str = Field("1.0.0")
    framework: str = Field("scikit-learn")
    dataset_identifier: str
    dataset_version: Optional[str] = None
    feature_engineering_version: str = Field("1.0.0")
    artifact_path: str = Field(..., description="Relative path under storage/models/")
    description: Optional[str] = None
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)
    training_manifest: Dict[str, Any] = Field(default_factory=dict)
    evaluation_manifest: Dict[str, Any] = Field(default_factory=dict)
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class ModelIntegrityResponse(BaseModel):
    model_id: str
    domain: str
    status: str
    artifact_path: str
    is_valid: bool
    expected_sha256: Optional[str] = None
    computed_sha256: Optional[str] = None
    file_size_bytes: Optional[int] = None
    verified_at: datetime
    details: Dict[str, Any] = Field(default_factory=dict)


class ModelGateEvaluationReport(BaseModel):
    can_promote: bool
    model_id: str
    domain: str
    policy_version: str
    passed_gates: List[str]
    failed_gates: List[str]
    gate_details: Dict[str, Any]


class ModelMonitoringSummary(BaseModel):
    domain: str
    active_model_id: Optional[str] = None
    active_model_version: Optional[str] = None
    status: str
    total_inferences: int
    last_inference_timestamp: Optional[datetime] = None
    data_classification: str = Field("OBSERVED", description="Classification of telemetry: OBSERVED, DERIVED, or UNAVAILABLE")
    distribution_summary: Dict[str, Any] = Field(default_factory=dict)
