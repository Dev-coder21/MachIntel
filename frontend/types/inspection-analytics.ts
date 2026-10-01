export interface ScoreHistogramBin {
  bin_start: number;
  bin_end: number;
  normal_count: number;
  defect_count: number;
  total_count: number;
}

export interface ScoreDistribution {
  run_id: string;
  threshold: number;
  overall_stats: Record<string, number>;
  normal_stats: Record<string, number>;
  defective_stats: Record<string, number>;
  histogram: ScoreHistogramBin[];
}

export interface DefectClassAnalyticsItem {
  defect_class: string;
  image_count: number;
  detected_count: number;
  missed_count: number;
  observed_detection_rate: number;
  mean_score: number;
  min_score: number;
  max_score: number;
}

export interface DefectClassAnalytics {
  run_id: string;
  category: string;
  classes: DefectClassAnalyticsItem[];
}

export interface ConfusionMatrixAnalytics {
  run_id: string;
  true_positives: number;
  true_negatives: number;
  false_positives: number;
  false_negatives: number;
  precision: number;
  recall: number;
  f1_score: number;
  specificity: number;
  image_roc_auc?: number | null;
  image_pr_auc?: number | null;
  threshold: number;
}

export interface LocalizationAnalytics {
  run_id: string;
  pixel_roc_auc?: number | null;
  mask_evaluated_images: number;
  has_localization: boolean;
  localization_method: string;
  resolution: string;
}

export interface InspectionRunProvenance {
  run_id: string;
  dataset_identifier: string;
  category: string;
  model_version: string;
  feature_config_version: string;
  policy_version: string;
  threshold: number;
  normal_training_stats: Record<string, unknown>;
  created_at: string;
}

export interface RunComparisonItem {
  run_id: string;
  model_version: string;
  policy_version: string;
  threshold: number;
  total_images: number;
  passed_count: number;
  defect_count: number;
  observed_defect_rate: number;
  roc_auc?: number | null;
  pr_auc?: number | null;
  precision?: number | null;
  recall?: number | null;
  f1_score?: number | null;
  pixel_roc_auc?: number | null;
  created_at: string;
}

export interface RunComparison {
  is_available: boolean;
  reason?: string | null;
  total_runs: number;
  runs: RunComparisonItem[];
}

export interface InspectionRunAnalyticsSummary {
  run_id: string;
  dataset_identifier: string;
  category: string;
  model_version: string;
  feature_config_version: string;
  policy_version: string;
  status: string;
  threshold: number;
  total_images: number;
  passed_count: number;
  defect_count: number;
  observed_defect_rate: number;
  score_min: number;
  score_max: number;
  score_mean: number;
  score_median: number;
  evaluation_metrics: Record<string, unknown>;
  created_at: string;
}
