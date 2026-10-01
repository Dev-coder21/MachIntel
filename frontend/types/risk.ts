import { OperationalState } from "./prediction";

export type RiskState = OperationalState;

export interface EvidenceItem {
  evidence_id: string;
  machine_id: string;
  evidence_type: string;
  source: string;
  source_reference: string;
  observation_cycle: number;
  observed_at: string | null;
  value: any;
  unit: string | null;
  confidence: number | null;
  provenance: Record<string, any>;
  model_version: string | null;
  feature_version: string | null;
  created_at: string;
}

export interface RiskAssessmentItem {
  id: string;
  machine_id: string;
  machine_name: string | null;
  prediction_id: string;
  risk_state: RiskState;
  health_index: number;
  predicted_rul: number;
  reason_codes: string[];
  explanation: string;
  policy_version: string;
  evidence_references: EvidenceItem[];
  created_at: string;
}

export interface RiskAssessmentListResponse {
  total: number;
  page: number;
  page_size: number;
  items: RiskAssessmentItem[];
}

export interface RiskTransitionItem {
  id: string;
  machine_id: string;
  machine_name: string | null;
  from_state: RiskState;
  to_state: RiskState;
  observation_cycle: number;
  created_at: string;
}
