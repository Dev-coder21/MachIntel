export type JobStatus = 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'CANCELLED';

export type JobType =
  | 'EVIDENCE_REFRESH'
  | 'RISK_REFRESH'
  | 'MAINTENANCE_RECOMMENDATION_REFRESH'
  | 'ANALYTICS_REFRESH';

export interface Job {
  id: string;
  job_type: JobType;
  status: JobStatus;
  execution_key: string | null;
  requested_by_id: string | null;
  attempt_count: number;
  max_attempts: number;
  error_code: string | null;
  error_message: string | null;
  payload: Record<string, any>;
  output_summary: Record<string, any>;
  retry_metadata: Record<string, any>;
  worker_id: string | null;
  duration_ms: number | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  heartbeat_at: string | null;
}

export interface JobListResponse {
  items: Job[];
  total: number;
  skip: number;
  limit: number;
}

export interface JobSummary {
  total_jobs: number;
  queued_count: number;
  running_count: number;
  succeeded_count: number;
  failed_count: number;
  cancelled_count: number;
  recent_jobs: Job[];
  last_refresh_by_type: Record<string, string | null>;
  active_workers_count: number;
}

export interface WorkerInstance {
  worker_id: string;
  hostname: string;
  pid: number;
  status: string;
  started_at: string;
  heartbeat_at: string;
  current_job_id: string | null;
  metadata_info?: Record<string, any>;
}

export interface WorkerHealth {
  status: string;
  worker_enabled: boolean;
  scheduler_enabled: boolean;
  database_connected: boolean;
  active_workers_count: number;
  active_workers: WorkerInstance[];
  timestamp: string;
}
