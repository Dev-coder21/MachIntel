from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class InspectionRunCreate(BaseModel):
    category: str = Field(default="metal_nut", description="MVTec AD category name")
    dataset_identifier: str = Field(default="MVTec-AD-metal_nut", description="Registered dataset identifier")
    model_version: str = Field(default="mvtec-patchcore-metalnut-v1.0.0", description="Model version")


class InspectionResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    split: str
    defect_class: str
    source_image_filename: str
    image_level_score: float
    decision: str
    ground_truth_label: str
    has_heatmap: bool = False
    has_overlay: bool = False
    has_ground_truth_mask: bool = False
    inference_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class InspectionRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
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
    evaluation_summary: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class InspectionRunSummaryResponse(BaseModel):
    run_id: uuid.UUID
    dataset_identifier: str
    category: str
    model_version: str
    policy_version: str
    threshold: float
    total_images: int
    passed_count: int
    defect_count: int
    defect_rate: float
    metrics: Dict[str, Any]
    defect_breakdown: Dict[str, Dict[str, Any]]
