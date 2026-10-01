export interface SensorSummaryItem {
  sensor_key: string;
  channel_name: string;
  engineering_unit: string;
  min_value: number;
  max_value: number;
  mean_value: number;
  std_value: number;
  initial_value: number;
  latest_value: number;
  net_change: number;
  pct_change: number | null;
  direction: "INCREASING" | "DECREASING" | "STABLE";
}

export interface MachineAnalyticsSummary {
  machine_id: string;
  machine_name: string;
  source_dataset: string;
  source_entity_id: string;
  split_category: string;
  status: string;
  first_cycle: number;
  latest_cycle: number;
  total_cycles: number;
  active_sensor_count: number;
  invariant_sensor_count: number;
  top_drifting_sensors: SensorSummaryItem[];
  sensors: SensorSummaryItem[];
}

export interface TrendPoint {
  cycle: number;
  raw_value: number;
  rolling_mean: number;
  rolling_std: number;
  rolling_min: number;
  rolling_max: number;
  rolling_slope: number;
}

export interface SensorTrendResponse {
  machine_id: string;
  sensor_key: string;
  channel_name: string;
  engineering_unit: string;
  window_size: number;
  total_cycles: number;
  returned_points: number;
  is_downsampled: boolean;
  direction: string;
  overall_slope: number;
  points: TrendPoint[];
}

export interface CorrelationMatrixResponse {
  machine_id: string;
  channels: string[];
  channel_names: string[];
  matrix: number[][];
}

export interface FeatureColumnMeta {
  name: string;
  source_channel: string;
  feature_type: string;
  window: number;
}

export interface FeaturePreviewRow {
  cycle: number;
  features: Record<string, number>;
}

export interface FeaturePreviewResponse {
  machine_id: string;
  feature_engineering_version: string;
  window_size: number;
  min_periods: number;
  scaling_policy: string;
  total_feature_count: number;
  columns: FeatureColumnMeta[];
  rows: FeaturePreviewRow[];
  disclaimer: string;
}

export interface MachineComparisonItem {
  machine_id: string;
  source_entity_id: string;
  split_category: string;
  status: string;
  total_cycles: number;
  max_cycle: number;
  ground_truth_rul: number | null;
  drift_t24: number;
  drift_t30: number;
  drift_t50: number;
  drift_p30: number;
  drift_nf: number;
  volatility_score: number;
}

export interface MachineComparisonResponse {
  machines: MachineComparisonItem[];
  compared_count: number;
}

export interface FleetAnalyticsOverviewResponse {
  total_machines: number;
  total_cycles: number;
  train_engines_count: number;
  val_engines_count: number;
  test_engines_count: number;
  avg_train_cycles: number;
  min_train_cycles: number;
  max_train_cycles: number;
  avg_test_cycles: number;
  min_test_cycles: number;
  max_test_cycles: number;
  active_sensor_channels: string[];
  invariant_sensor_channels: string[];
  cycle_distribution_buckets: Record<string, number>;
}
