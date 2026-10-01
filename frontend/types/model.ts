export interface ModelMetrics {
  val_rmse?: number;
  val_phm_score?: number;
  test_rmse?: number;
  test_phm_score?: number;
  roc_auc?: number;
  pr_auc?: number;
  precision?: number;
  recall?: number;
  f1_score?: number;
  pixel_roc_auc?: number;
  train_samples?: number;
  val_samples?: number;
  test_samples?: number;
}

export interface ModelEvaluationItem {
  id: string;
  model_version_id: string;
  evaluation_type: string;
  dataset_identifier: string;
  split: string;
  metrics: Record<string, any>;
  manifest: Record<string, any>;
  gate_result: string;
  gate_details: Record<string, any>;
  evaluator: string;
  evaluated_at: string;
  created_at: string;
}

export interface ModelPromotionItem {
  id: string;
  model_version_id: string;
  from_status: string;
  to_status: string;
  promoted_by_id?: string | null;
  reason: string;
  promotion_policy_version: string;
  gate_results: Record<string, any>;
  promoted_at: string;
  created_at: string;
}

export interface ModelIntegrityReport {
  model_id: string;
  domain: string;
  status: string;
  artifact_path: string;
  is_valid: boolean;
  expected_sha256?: string | null;
  computed_sha256?: string | null;
  file_size_bytes?: number | null;
  verified_at: string;
  details: Record<string, any>;
}

export interface ModelGateReport {
  can_promote: boolean;
  model_id: string;
  domain: string;
  policy_version: string;
  passed_gates: string[];
  failed_gates: string[];
  gate_details: Record<string, any>;
}

export interface ModelMonitoringSummary {
  domain: string;
  active_model_id?: string | null;
  active_model_version?: string | null;
  status: string;
  total_inferences: number;
  last_inference_timestamp?: string | null;
  data_classification: string;
  distribution_summary: Record<string, any>;
}

export interface ModelRegistryItem {
  id: string;
  model_id: string;
  model_name: string;
  domain?: string;
  model_family?: string;
  algorithm: string;
  task: string;
  version?: string;
  status?: string;
  framework?: string;
  dataset_identifier: string;
  dataset_version?: string | null;
  feature_engineering_version: string;
  feature_version?: string | null;
  preprocessing_version: string;
  window_size: number;
  hyperparameters: Record<string, any>;
  metrics: Record<string, any>;
  feature_names?: string[];
  feature_importances?: Record<string, number>;
  artifact_path: string;
  artifact_sha256?: string | null;
  artifact_size_bytes?: number | null;
  training_manifest?: Record<string, any>;
  evaluation_manifest?: Record<string, any>;
  description?: string | null;
  metadata_json?: Record<string, any>;
  parent_model_id?: string | null;
  is_active: boolean;
  registered_at?: string;
  created_at: string;
  updated_at?: string | null;
}

export interface ModelRegistryListResponse {
  total: number;
  active_machine_health_model_id?: string | null;
  active_visual_inspection_model_id?: string | null;
  active_model_id?: string | null;
  items: ModelRegistryItem[];
}
