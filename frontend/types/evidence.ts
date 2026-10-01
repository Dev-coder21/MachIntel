export type EvidenceDomain = "MACHINE_HEALTH" | "VISUAL_INSPECTION";

export type EvidenceEntityType =
  | "MACHINE"
  | "INSPECTION_RUN"
  | "INSPECTION_RESULT"
  | "PREDICTION"
  | "RISK_ASSESSMENT"
  | "ALERT";

export type EvidenceType =
  | "TELEMETRY"
  | "FEATURE"
  | "RUL_PREDICTION"
  | "HEALTH_INDEX"
  | "RISK_ASSESSMENT"
  | "RISK_REASON"
  | "ALERT"
  | "IMAGE"
  | "ANOMALY_SCORE"
  | "INSPECTION_DECISION"
  | "LOCALIZATION"
  | "GROUND_TRUTH"
  | "ANALYTICS"
  | "MODEL_ARTIFACT"
  | "DATASET_PROVENANCE";

export type EvidenceQualityState =
  | "VERIFIED"
  | "DERIVED"
  | "BENCHMARK_GROUND_TRUTH"
  | "PROVENANCE_ONLY"
  | "UNAVAILABLE";

export type EvidenceRelationshipType =
  | "DERIVED_FROM"
  | "SUPPORTED_BY"
  | "PRODUCED_BY"
  | "EVALUATED_AGAINST"
  | "TRIGGERED"
  | "BELONGS_TO"
  | "HAS_ARTIFACT"
  | "HAS_PROVENANCE";

export interface EvidenceRecord {
  id: string;
  domain: EvidenceDomain;
  entity_type: EvidenceEntityType;
  entity_id: string;
  evidence_type: EvidenceType;
  source: string;
  source_reference: string;
  observation_time?: string | null;
  observation_cycle?: number | null;
  value?: Record<string, any> | null;
  unit?: string | null;
  confidence?: number | null;
  quality_state: EvidenceQualityState;
  explanation?: string | null;
  provenance: Record<string, any>;
  model_version?: string | null;
  feature_version?: string | null;
  policy_version?: string | null;
  created_at: string;
}

export interface EvidenceRelationship {
  id: string;
  source_evidence_id: string;
  target_evidence_id: string;
  relationship_type: EvidenceRelationshipType;
  relationship_metadata: Record<string, any>;
  created_at: string;
  source_evidence?: EvidenceRecord | null;
  target_evidence?: EvidenceRecord | null;
}

export interface EvidenceBundleItem {
  id: string;
  bundle_id: string;
  evidence_id: string;
  display_order: number;
  role_in_bundle: string;
  evidence?: EvidenceRecord | null;
}

export interface EvidenceBundle {
  id: string;
  bundle_name: string;
  domain: EvidenceDomain;
  entity_type: EvidenceEntityType;
  entity_id: string;
  description?: string | null;
  items: EvidenceBundleItem[];
  created_at: string;
}

export interface EvidenceTimelineItem {
  id: string;
  domain: EvidenceDomain;
  entity_type: EvidenceEntityType;
  entity_id: string;
  evidence_type: EvidenceType;
  source: string;
  observation_cycle?: number | null;
  observation_time?: string | null;
  value?: Record<string, any> | null;
  quality_state: EvidenceQualityState;
  explanation?: string | null;
  created_at: string;
}

export interface EvidenceProvenance {
  evidence_id: string;
  domain: EvidenceDomain;
  entity_type: EvidenceEntityType;
  entity_id: string;
  evidence_type: EvidenceType;
  source: string;
  source_reference: string;
  provenance: Record<string, any>;
  model_version?: string | null;
  feature_version?: string | null;
  policy_version?: string | null;
  quality_state: EvidenceQualityState;
  created_at: string;
}

export interface EvidenceSearchResponse {
  total: number;
  records: EvidenceRecord[];
  domain?: EvidenceDomain | null;
}
