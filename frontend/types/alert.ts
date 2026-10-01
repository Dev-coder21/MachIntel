export type AlertSeverity = 'INFO' | 'WARNING' | 'CRITICAL';
export type AlertStatus = 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';

export interface AlertItem {
  id: string;
  machine_id: string;
  risk_assessment_id: string;
  severity: AlertSeverity;
  status: AlertStatus;
  title: string;
  description: string;
  reason_codes: string[];
  created_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  acknowledged_by: string | null;
  resolved_by: string | null;
}

export interface AlertListResponse {
  alerts: AlertItem[];
  total: number;
  skip: number;
  limit: number;
}

export interface AlertSummary {
  total: number;
  open: number;
  acknowledged: number;
  resolved: number;
  by_severity: {
    INFO: number;
    WARNING: number;
    CRITICAL: number;
  };
}
