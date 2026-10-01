from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class SensorSummaryItem(BaseModel):
    sensor_key: str
    channel_name: str
    engineering_unit: str
    min_value: float
    max_value: float
    mean_value: float
    std_value: float
    initial_value: float
    latest_value: float
    net_change: float
    pct_change: Optional[float] = None
    direction: str  # INCREASING, DECREASING, STABLE


class MachineAnalyticsSummary(BaseModel):
    machine_id: str
    machine_name: str
    source_dataset: str
    source_entity_id: str
    split_category: str
    status: str
    first_cycle: int
    latest_cycle: int
    total_cycles: int
    active_sensor_count: int
    invariant_sensor_count: int
    top_drifting_sensors: List[SensorSummaryItem]
    sensors: List[SensorSummaryItem]


class TrendPoint(BaseModel):
    cycle: int
    raw_value: float
    rolling_mean: float
    rolling_std: float
    rolling_min: float
    rolling_max: float
    rolling_slope: float


class SensorTrendResponse(BaseModel):
    machine_id: str
    sensor_key: str
    channel_name: str
    engineering_unit: str
    window_size: int
    total_cycles: int
    returned_points: int
    is_downsampled: bool
    direction: str
    overall_slope: float
    points: List[TrendPoint]


class CorrelationMatrixResponse(BaseModel):
    machine_id: str
    channels: List[str]
    channel_names: List[str]
    matrix: List[List[float]]


class FeatureColumnMeta(BaseModel):
    name: str
    source_channel: str
    feature_type: str  # RAW, ROLLING_MEAN, ROLLING_STD, ROLLING_MIN, ROLLING_MAX, ROLLING_SLOPE
    window: int


class FeaturePreviewRow(BaseModel):
    cycle: int
    features: Dict[str, float]


class FeaturePreviewResponse(BaseModel):
    machine_id: str
    feature_engineering_version: str
    window_size: int
    min_periods: int
    scaling_policy: str
    total_feature_count: int
    columns: List[FeatureColumnMeta]
    rows: List[FeaturePreviewRow]
    disclaimer: str = Field(
        default="DERIVED ANALYTICAL FEATURES ONLY. No ML predictions, Health Index, or RUL estimations.",
        description="Explicit notice confirming absence of ML prediction fabrication.",
    )


class MachineComparisonItem(BaseModel):
    machine_id: str
    source_entity_id: str
    split_category: str
    status: str
    total_cycles: int
    max_cycle: int
    ground_truth_rul: Optional[int] = None
    drift_t24: float  # Sensor 2
    drift_t30: float  # Sensor 3
    drift_t50: float  # Sensor 4
    drift_p30: float  # Sensor 7
    drift_nf: float   # Sensor 8
    volatility_score: float


class MachineComparisonResponse(BaseModel):
    machines: List[MachineComparisonItem]
    compared_count: int


class FleetAnalyticsOverviewResponse(BaseModel):
    total_machines: int
    total_cycles: int
    train_engines_count: int
    val_engines_count: int
    test_engines_count: int
    avg_train_cycles: float
    min_train_cycles: int
    max_train_cycles: int
    avg_test_cycles: float
    min_test_cycles: int
    max_test_cycles: int
    active_sensor_channels: List[str]
    invariant_sensor_channels: List[str]
    cycle_distribution_buckets: Dict[str, int]
