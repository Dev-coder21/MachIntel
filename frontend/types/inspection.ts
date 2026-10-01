export interface DefectClassSummary {
  total_images: number;
  passed_count: number;
  defect_count: number;
  accuracy: number;
  mean_score: number;
  min_score: number;
  max_score: number;
}

export interface ConfusionMatrix {
  true_negative: number;
  false_positive: number;
  false_negative: number;
  true_positive: number;
}

export interface ImageLevelMetrics {
  roc_auc: number;
  pr_auc: number;
  precision: number;
  recall: number;
  f1_score: number;
  confusion_matrix: ConfusionMatrix;
}

export interface PixelLevelMetrics {
  pixel_roc_auc?: number | null;
  mask_evaluated_images?: number;
}

export interface InspectionEvaluationSummary {
  model_version?: string;
  feature_config_version?: string;
  policy_version?: string;
  dataset_identifier?: string;
  category?: string;
  threshold?: number;
  total_images_evaluated?: number;
  passed_count?: number;
  defect_count?: number;
  image_level_metrics?: ImageLevelMetrics;
  pixel_level_metrics?: PixelLevelMetrics;
  defect_breakdown?: Record<string, DefectClassSummary>;
  evaluation_timestamp?: string;
}

export interface InspectionRun {
  id: string;
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
  evaluation_summary: InspectionEvaluationSummary;
  created_at: string;
}

export interface InspectionResult {
  id: string;
  run_id: string;
  split: string;
  defect_class: string;
  source_image_filename: string;
  image_level_score: number;
  decision: "PASS" | "DEFECT";
  ground_truth_label: "PASS" | "DEFECT";
  has_heatmap: boolean;
  has_overlay: boolean;
  has_ground_truth_mask: boolean;
  inference_metadata: {
    model_version?: string;
    backbone?: string;
    feature_layers?: string[];
    subsample_ratio?: number;
    device?: string;
    inference_time_ms?: number;
    [key: string]: unknown;
  };
  created_at: string;
}

export interface InspectionRunSummary {
  run_id: string;
  dataset_identifier: string;
  category: string;
  model_version: string;
  policy_version: string;
  threshold: number;
  total_images: number;
  passed_count: number;
  defect_count: number;
  defect_rate: number;
  metrics: ImageLevelMetrics;
  defect_breakdown: Record<string, DefectClassSummary>;
}
