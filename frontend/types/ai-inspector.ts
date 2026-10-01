export interface InvestigationContext {
  machine_id?: string;
  inspection_run_id?: string;
  inspection_result_id?: string;
  domain?: "MACHINE_HEALTH" | "VISUAL_INSPECTION" | string;
}

export interface InvestigationCreateRequest {
  question: string;
  context?: InvestigationContext;
}

export interface EvidenceCitation {
  evidence_id: string;
  domain: "MACHINE_HEALTH" | "VISUAL_INSPECTION" | string;
  type: string;
  source: string;
  observation_cycle?: number | null;
  quality_state: string;
  explanation?: string | null;
  value_summary?: string | null;
}

export interface ToolCallRecord {
  tool_name: string;
  arguments: Record<string, any>;
  status: "SUCCESS" | "FAILED" | "TIMEOUT" | string;
  duration_ms: number;
  evidence_ids_returned: string[];
}

export interface InvestigationTrace {
  tool_calls: ToolCallRecord[];
  domains_consulted: string[];
  completed: boolean;
}

export interface AIInvestigationResponse {
  id: string;
  question: string;
  status: "COMPLETED" | "FAILED" | "PROVIDER_UNAVAILABLE" | string;
  answer: string;
  evidence: EvidenceCitation[];
  limitations: string[];
  investigation: InvestigationTrace;
  provider: string;
  model: string;
  created_at: string;
  completed_at?: string | null;
  error_message?: string | null;
}

export interface AIInvestigationSummary {
  id: string;
  question: string;
  status: string;
  provider: string;
  model: string;
  domains_consulted: string[];
  evidence_count: number;
  started_at: string;
  completed_at?: string | null;
}

export interface ToolDefinitionSchema {
  name: string;
  description: string;
  domain: string;
  read_only: boolean;
  parameters: Record<string, any>;
}
