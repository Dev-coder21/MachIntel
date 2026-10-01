export type MaintenancePriority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type MaintenanceStatus = "OPEN" | "ACKNOWLEDGED" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";

export type MaintenanceSourceDomain = "MACHINE_HEALTH" | "VISUAL_INSPECTION";

export type MaintenanceSourceType = "RISK_ASSESSMENT" | "ALERT" | "INSPECTION_RESULT" | "EVIDENCE_BUNDLE";

export interface MaintenanceEvent {
  id: string;
  work_order_id: string;
  event_type: string;
  from_status?: string | null;
  to_status: string;
  actor_id?: string | null;
  notes?: string | null;
  event_metadata: Record<string, unknown>;
  created_at: string;
}

export interface MaintenanceWorkOrder {
  id: string;
  machine_id?: string | null;
  source_domain: string;
  source_type: string;
  source_reference: string;
  deduplication_key: string;
  title: string;
  description: string;
  priority: MaintenancePriority;
  status: MaintenanceStatus;
  recommended_action: string;
  reason: string;
  risk_state_at_creation?: string | null;
  predicted_rul_at_creation?: number | null;
  health_index_at_creation?: number | null;
  anomaly_score_at_creation?: number | null;
  policy_version: string;
  evidence_references: Record<string, unknown>[];
  created_by_id?: string | null;
  assigned_to_id?: string | null;
  created_at: string;
  acknowledged_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  cancelled_at?: string | null;
  updated_at: string;
  resolution_notes?: string | null;
}

export interface MaintenanceWorkOrderDetail extends MaintenanceWorkOrder {
  events: MaintenanceEvent[];
  source_entity_details?: Record<string, unknown> | null;
}

export interface MaintenanceSummary {
  total_work_orders: number;
  open_count: number;
  acknowledged_count: number;
  in_progress_count: number;
  completed_count: number;
  cancelled_count: number;
  critical_priority_count: number;
  high_priority_count: number;
  medium_priority_count: number;
  low_priority_count: number;
  machine_health_count: number;
  visual_inspection_count: number;
  recent_activity: MaintenanceEvent[];
}

export interface CreateWorkOrderPayload {
  machine_id?: string;
  source_domain: MaintenanceSourceDomain;
  source_type: MaintenanceSourceType;
  source_reference: string;
  title?: string;
  description?: string;
  priority?: MaintenancePriority;
  recommended_action?: string;
  reason?: string;
  assigned_to_id?: string;
}
