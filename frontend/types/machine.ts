export type MachineType = "TURBOFAN_ENGINE" | "OPTICAL_INSPECTION_STATION" | "ROTATING_ASSET";
export type MachineStatus = "OPERATIONAL" | "MAINTENANCE" | "DEGRADED" | "OFFLINE";
export type SplitCategory = "INTERNAL_TRAIN" | "INTERNAL_VAL" | "EVAL_TEST";

export interface Machine {
  id: string;
  machine_id: string;
  name: string;
  machine_type: MachineType;
  source_dataset: string;
  source_entity_id: string;
  dataset_id?: string;
  status: MachineStatus;
  split_category: SplitCategory;
  total_cycles: number;
  max_cycle: number;
  ground_truth_rul?: number | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface MachineDetail extends Machine {
  active_sensor_channels: string[];
  invariant_sensor_channels: string[];
  quality_issues_count: number;
}

export interface MachineListResponse {
  items: Machine[];
  total: number;
  skip: number;
  limit: number;
}

export interface FoundationStats {
  total_machines: number;
  total_telemetry_records: number;
  operational_count: number;
  degraded_count: number;
  maintenance_count: number;
  datasets_registered: number;
}
