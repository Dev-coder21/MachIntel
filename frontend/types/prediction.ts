export type OperationalState = 'NORMAL' | 'WATCH' | 'ELEVATED' | 'CRITICAL';

export interface PredictionItem {
  id: string;
  machine_id: string;
  machine_name: string;
  model_version: string;
  dataset_version: string;
  feature_version: string;
  observation_cycle: number;
  predicted_rul: number;
  health_index: number;
  operational_state: OperationalState;
  created_at: string;
  metadata_json: Record<string, any>;
}

export interface PredictionListResponse {
  total: number;
  page: number;
  page_size: number;
  items: PredictionItem[];
}

export interface FleetPrognosticsOverview {
  total_machines: number;
  machines_with_predictions: number;
  active_model_id: string;
  active_model_algorithm: string;
  average_predicted_rul: number | null;
  average_health_index: number | null;
  state_distribution: Record<OperationalState, number>;
}

export interface PredictionCreateRequest {
  observation_cycle?: number;
  model_version?: string;
}
