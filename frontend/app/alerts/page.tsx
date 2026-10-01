"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { StatusBadge } from "@/components/common/StatusBadge";
import { LoadingSkeleton } from "@/components/common/LoadingSkeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { useAuth } from "@/lib/auth-context";
import { apiClient } from "@/lib/api-client";
import { AlertItem, AlertSummary, AlertStatus, AlertSeverity } from "@/types/alert";

export default function AlertsPage() {
  const { user } = useAuth();
  const canMutate = user && user.role !== "VIEWER";

  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [summary, setSummary] = useState<AlertSummary | null>(null);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Action state
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const [modalAction, setModalAction] = useState<{
    type: "acknowledge" | "resolve";
    alert: AlertItem;
  } | null>(null);
  const [actionNote, setActionNote] = useState<string>("");

  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const params: { status?: string; severity?: string; limit: number } = { limit: 100 };
      if (statusFilter !== "ALL") params.status = statusFilter;
      if (severityFilter !== "ALL") params.severity = severityFilter;

      const [alertsRes, summaryRes] = await Promise.all([
        apiClient.getAlerts(params),
        apiClient.getAlertSummary(),
      ]);

      setAlerts(alertsRes.alerts);
      setTotalCount(alertsRes.total);
      setSummary(summaryRes);
    } catch (err: any) {
      console.error("Failed to load alerts:", err);
      setError(err?.message || "Failed to load operational alerts from database.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, severityFilter]);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  const handleExecuteAction = async () => {
    if (!modalAction) return;
    const { type, alert } = modalAction;
    try {
      setActionInProgress(alert.id);
      if (type === "acknowledge") {
        await apiClient.acknowledgeAlert(alert.id, actionNote || undefined);
      } else {
        await apiClient.resolveAlert(alert.id, actionNote || undefined);
      }
      setModalAction(null);
      setActionNote("");
      await fetchAlerts();
    } catch (err: any) {
      setError(err?.message || `Failed to ${type} alert`);
    } finally {
      setActionInProgress(null);
    }
  };

  return (
    <AppShell>
      <PageHeader
        title="Industrial Alert Console"
        subtitle="Operational triage queue driven deterministically by RUL prognostic thresholds and analytical risk policy."
        breadcrumbs={[{ label: "Intelligence" }, { label: "Alert Console" }]}
      />

      {/* Summary KPI Ribbon */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: 16,
          marginBottom: 24,
        }}
      >
        <div className="panel" style={{ padding: "16px 20px" }}>
          <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Total Recorded Alerts
          </div>
          <div style={{ fontSize: 24, fontWeight: 700, fontFamily: "var(--font-mono)", marginTop: 6, color: "var(--text-primary)" }}>
            {summary ? summary.total : "—"}
          </div>
        </div>

        <div className="panel" style={{ padding: "16px 20px", borderLeft: "3px solid var(--risk-elevated)" }}>
          <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Active Open Alerts
          </div>
          <div style={{ fontSize: 24, fontWeight: 700, fontFamily: "var(--font-mono)", marginTop: 6, color: "var(--risk-elevated)" }}>
            {summary ? summary.open : "—"}
          </div>
        </div>

        <div className="panel" style={{ padding: "16px 20px", borderLeft: "3px solid var(--risk-critical)" }}>
          <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Critical Severity Alerts
          </div>
          <div style={{ fontSize: 24, fontWeight: 700, fontFamily: "var(--font-mono)", marginTop: 6, color: "var(--risk-critical)" }}>
            {summary ? summary.by_severity.CRITICAL : "—"}
          </div>
        </div>

        <div className="panel" style={{ padding: "16px 20px", borderLeft: "3px solid #A78BFA" }}>
          <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Acknowledged / In Triage
          </div>
          <div style={{ fontSize: 24, fontWeight: 700, fontFamily: "var(--font-mono)", marginTop: 6, color: "#A78BFA" }}>
            {summary ? summary.acknowledged : "—"}
          </div>
        </div>

        <div className="panel" style={{ padding: "16px 20px", borderLeft: "3px solid var(--risk-normal)" }}>
          <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Resolved
          </div>
          <div style={{ fontSize: 24, fontWeight: 700, fontFamily: "var(--font-mono)", marginTop: 6, color: "var(--risk-normal)" }}>
            {summary ? summary.resolved : "—"}
          </div>
        </div>
      </div>

      {/* Filter and Control Bar */}
      <div
        className="panel"
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 16,
          padding: "12px 20px",
          marginBottom: 20,
        }}
      >
        {/* Status Filters */}
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginRight: 4 }}>
            STATUS:
          </span>
          {["ALL", "OPEN", "ACKNOWLEDGED", "RESOLVED"].map((tab) => (
            <button
              key={tab}
              onClick={() => setStatusFilter(tab)}
              style={{
                padding: "6px 12px",
                backgroundColor: statusFilter === tab ? "var(--accent-cyan-glow)" : "var(--bg-surface)",
                color: statusFilter === tab ? "var(--accent-cyan)" : "var(--text-secondary)",
                border: `1px solid ${statusFilter === tab ? "var(--accent-cyan)" : "var(--border-default)"}`,
                borderRadius: "var(--radius-sm)",
                fontSize: 11,
                fontWeight: 600,
                fontFamily: "var(--font-mono)",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Severity Filters */}
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginRight: 4 }}>
            SEVERITY:
          </span>
          {["ALL", "CRITICAL", "WARNING", "INFO"].map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              style={{
                padding: "6px 12px",
                backgroundColor: severityFilter === sev ? "rgba(255, 255, 255, 0.08)" : "transparent",
                color:
                  sev === "CRITICAL"
                    ? "var(--risk-critical)"
                    : sev === "WARNING"
                    ? "var(--risk-elevated)"
                    : sev === "INFO"
                    ? "var(--risk-watch)"
                    : "var(--text-secondary)",
                border: `1px solid ${severityFilter === sev ? "var(--border-focus)" : "var(--border-subtle)"}`,
                borderRadius: "var(--radius-sm)",
                fontSize: 11,
                fontWeight: 600,
                fontFamily: "var(--font-mono)",
                cursor: "pointer",
              }}
            >
              {sev}
            </button>
          ))}
        </div>

        {/* Refresh & Role Badge */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span
            style={{
              fontSize: 11,
              fontFamily: "var(--font-mono)",
              color: canMutate ? "var(--accent-cyan)" : "var(--text-muted)",
              padding: "4px 8px",
              backgroundColor: canMutate ? "var(--accent-cyan-glow)" : "rgba(255, 255, 255, 0.04)",
              borderRadius: "var(--radius-sm)",
              border: `1px solid ${canMutate ? "rgba(0, 229, 255, 0.2)" : "var(--border-subtle)"}`,
            }}
          >
            {user ? `${user.role} ACCESS` : "READ-ONLY"}
          </span>
          <button
            onClick={() => fetchAlerts()}
            style={{
              padding: "6px 12px",
              backgroundColor: "var(--bg-surface)",
              color: "var(--text-secondary)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-sm)",
              fontSize: 11,
              fontFamily: "var(--font-mono)",
              cursor: "pointer",
            }}
          >
            ↻ REFRESH
          </button>
        </div>
      </div>

      {/* Main Alert List / Table */}
      {loading ? (
        <div className="panel" style={{ padding: 24 }}>
          <LoadingSkeleton count={6} />
        </div>
      ) : error ? (
        <ErrorState message={error} onRetry={fetchAlerts} />
      ) : alerts.length === 0 ? (
        <EmptyState
          icon="alert"
          metadataTag="ALERT QUEUE CLEAR"
          title="No Matching Alerts Found"
          description={`No operational alerts match status "${statusFilter}" and severity "${severityFilter}". Risk assessments evaluate deterministically against versioned policy thresholds.`}
        />
      ) : (
        <div className="panel" style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: 13 }}>
            <thead>
              <tr
                style={{
                  borderBottom: "1px solid var(--border-default)",
                  backgroundColor: "rgba(255, 255, 255, 0.02)",
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                  color: "var(--text-muted)",
                  textTransform: "uppercase",
                }}
              >
                <th style={{ padding: "12px 16px" }}>Severity</th>
                <th style={{ padding: "12px 16px" }}>Status</th>
                <th style={{ padding: "12px 16px" }}>Machine</th>
                <th style={{ padding: "12px 16px" }}>Alert Title & Reason</th>
                <th style={{ padding: "12px 16px" }}>Created</th>
                <th style={{ padding: "12px 16px" }}>Audit Trail</th>
                <th style={{ padding: "12px 16px", textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((alert) => (
                <tr
                  key={alert.id}
                  style={{
                    borderBottom: "1px solid var(--border-subtle)",
                    transition: "background 0.15s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.02)")}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                >
                  <td style={{ padding: "14px 16px" }}>
                    <StatusBadge status={alert.severity} />
                  </td>

                  <td style={{ padding: "14px 16px" }}>
                    <StatusBadge status={alert.status} />
                  </td>

                  <td style={{ padding: "14px 16px" }}>
                    <Link
                      href={`/machines/${alert.machine_id}?tab=prognostics`}
                      style={{
                        fontFamily: "var(--font-mono)",
                        color: "var(--accent-cyan)",
                        fontWeight: 600,
                        textDecoration: "none",
                      }}
                    >
                      {alert.machine_id.slice(0, 8)}...
                    </Link>
                  </td>

                  <td style={{ padding: "14px 16px", maxWidth: 360 }}>
                    <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                      {alert.title}
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 6 }}>
                      {alert.description}
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                      {alert.reason_codes.map((code) => (
                        <span
                          key={code}
                          style={{
                            fontSize: 10,
                            fontFamily: "var(--font-mono)",
                            backgroundColor: "rgba(255, 255, 255, 0.05)",
                            color: "var(--text-muted)",
                            padding: "2px 6px",
                            borderRadius: "var(--radius-sm)",
                            border: "1px solid var(--border-subtle)",
                          }}
                        >
                          {code}
                        </span>
                      ))}
                    </div>
                  </td>

                  <td style={{ padding: "14px 16px", fontSize: 12, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                    {new Date(alert.created_at).toLocaleString([], {
                      dateStyle: "short",
                      timeStyle: "short",
                    })}
                  </td>

                  <td style={{ padding: "14px 16px", fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                    {alert.acknowledged_at && (
                      <div style={{ color: "#A78BFA", marginBottom: 2 }}>
                        Ack: {new Date(alert.acknowledged_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        {alert.acknowledged_by ? ` (${alert.acknowledged_by.slice(0, 8)})` : ""}
                      </div>
                    )}
                    {alert.resolved_at && (
                      <div style={{ color: "var(--risk-normal)" }}>
                        Res: {new Date(alert.resolved_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        {alert.resolved_by ? ` (${alert.resolved_by.slice(0, 8)})` : ""}
                      </div>
                    )}
                    {!alert.acknowledged_at && !alert.resolved_at && (
                      <span style={{ color: "var(--text-muted)" }}>Unassigned</span>
                    )}
                  </td>

                  <td style={{ padding: "14px 16px", textAlign: "right" }}>
                    {canMutate ? (
                      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
                        {alert.status === "OPEN" && (
                          <button
                            onClick={() => {
                              setModalAction({ type: "acknowledge", alert });
                              setActionNote("");
                            }}
                            disabled={actionInProgress === alert.id}
                            style={{
                              padding: "5px 10px",
                              backgroundColor: "rgba(167, 139, 250, 0.12)",
                              color: "#A78BFA",
                              border: "1px solid rgba(167, 139, 250, 0.3)",
                              borderRadius: "var(--radius-sm)",
                              fontSize: 11,
                              fontFamily: "var(--font-mono)",
                              cursor: "pointer",
                            }}
                          >
                            Acknowledge
                          </button>
                        )}

                        {alert.status !== "RESOLVED" && (
                          <button
                            onClick={() => {
                              setModalAction({ type: "resolve", alert });
                              setActionNote("");
                            }}
                            disabled={actionInProgress === alert.id}
                            style={{
                              padding: "5px 10px",
                              backgroundColor: "rgba(16, 185, 129, 0.12)",
                              color: "var(--risk-normal)",
                              border: "1px solid rgba(16, 185, 129, 0.3)",
                              borderRadius: "var(--radius-sm)",
                              fontSize: 11,
                              fontFamily: "var(--font-mono)",
                              cursor: "pointer",
                            }}
                          >
                            Resolve
                          </button>
                        )}

                        {alert.status === "RESOLVED" && (
                          <span style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                            Resolved
                          </span>
                        )}
                      </div>
                    ) : (
                      <span
                        style={{
                          fontSize: 10,
                          color: "var(--text-muted)",
                          fontFamily: "var(--font-mono)",
                          fontStyle: "italic",
                        }}
                      >
                        Viewer Read-Only
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Confirmation Action Modal */}
      {modalAction && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(4px)",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            zIndex: 1000,
          }}
        >
          <div
            className="panel"
            style={{
              width: "100%",
              maxWidth: 480,
              padding: 24,
              boxShadow: "0 20px 40px rgba(0, 0, 0, 0.6)",
            }}
          >
            <div style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", marginBottom: 8 }}>
              {modalAction.type === "acknowledge" ? "Acknowledge Alert" : "Resolve Alert"}
            </div>

            <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 16 }}>
              {modalAction.type === "acknowledge"
                ? `Mark alert "${modalAction.alert.title}" as acknowledged and in active investigation. This transitions alert status from OPEN to ACKNOWLEDGED with an audit log entry.`
                : `Resolve alert "${modalAction.alert.title}". This marks the machine condition as handled and updates the audit log.`}
            </p>

            <div style={{ marginBottom: 16 }}>
              <label
                style={{
                  display: "block",
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  color: "var(--text-muted)",
                  marginBottom: 6,
                }}
              >
                OPTIONAL TRIAGE NOTE / RESOLUTION COMMENT:
              </label>
              <textarea
                value={actionNote}
                onChange={(e) => setActionNote(e.target.value)}
                placeholder="e.g. Engine scheduled for borescope inspection during next planned downtime..."
                rows={3}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  backgroundColor: "var(--bg-input)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--text-primary)",
                  fontSize: 12,
                  fontFamily: "inherit",
                }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 12 }}>
              <button
                onClick={() => {
                  setModalAction(null);
                  setActionNote("");
                }}
                disabled={actionInProgress !== null}
                style={{
                  padding: "8px 16px",
                  backgroundColor: "transparent",
                  color: "var(--text-secondary)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: 12,
                  fontFamily: "var(--font-mono)",
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>

              <button
                onClick={handleExecuteAction}
                disabled={actionInProgress !== null}
                style={{
                  padding: "8px 18px",
                  backgroundColor:
                    modalAction.type === "acknowledge" ? "#A78BFA" : "var(--risk-normal)",
                  color: "#0B0F17",
                  border: "none",
                  borderRadius: "var(--radius-sm)",
                  fontSize: 12,
                  fontWeight: 600,
                  fontFamily: "var(--font-mono)",
                  cursor: "pointer",
                }}
              >
                {actionInProgress
                  ? "Recording Audit..."
                  : modalAction.type === "acknowledge"
                  ? "Confirm Acknowledgment"
                  : "Confirm Resolution"}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
