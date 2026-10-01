"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { LoadingSkeleton } from "@/components/common/LoadingSkeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { useAuth } from "@/lib/auth-context";
import { apiClient } from "@/lib/api-client";
import {
  MaintenancePriority,
  MaintenanceStatus,
  MaintenanceSourceDomain,
  MaintenanceSourceType,
  MaintenanceSummary,
  MaintenanceWorkOrder,
  MaintenanceWorkOrderDetail,
} from "@/types/maintenance";
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  ExternalLink,
  FileText,
  Filter,
  Layers,
  Play,
  Plus,
  RefreshCw,
  ShieldAlert,
  User as UserIcon,
  X,
  XCircle,
} from "lucide-react";

export default function MaintenancePage() {
  const { user } = useAuth();
  const canMutate = user && user.role !== "VIEWER";

  // Data states
  const [summary, setSummary] = useState<MaintenanceSummary | null>(null);
  const [workOrders, setWorkOrders] = useState<MaintenanceWorkOrder[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<MaintenanceWorkOrderDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [priorityFilter, setPriorityFilter] = useState<string>("ALL");
  const [domainFilter, setDomainFilter] = useState<string>("ALL");

  // Lifecycle Modals / Action states
  const [actionInProgress, setActionInProgress] = useState<boolean>(false);
  const [actionModal, setActionModal] = useState<{
    type: "acknowledge" | "start" | "complete" | "cancel";
    workOrderId: string;
  } | null>(null);
  const [actionNotes, setActionNotes] = useState<string>("");
  const [actionError, setActionError] = useState<string | null>(null);

  // Create Recommendation Modal
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [createForm, setCreateForm] = useState<{
    source_domain: MaintenanceSourceDomain;
    source_type: MaintenanceSourceType;
    source_reference: string;
    priority?: MaintenancePriority;
    notes?: string;
  }>({
    source_domain: "MACHINE_HEALTH",
    source_type: "RISK_ASSESSMENT",
    source_reference: "",
  });
  const [createError, setCreateError] = useState<string | null>(null);

  const fetchWorkOrders = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const params: {
        status?: string;
        priority?: string;
        source_domain?: string;
        limit: number;
      } = { limit: 100 };

      if (statusFilter !== "ALL") params.status = statusFilter;
      if (priorityFilter !== "ALL") params.priority = priorityFilter;
      if (domainFilter !== "ALL") params.source_domain = domainFilter;

      const [woList, summaryData] = await Promise.all([
        apiClient.listWorkOrders(params),
        apiClient.getMaintenanceSummary(),
      ]);

      setWorkOrders(woList);
      setSummary(summaryData);

      // Auto-select first item if none selected and list is non-empty
      if (!selectedId && woList.length > 0) {
        setSelectedId(woList[0].id);
      }
    } catch (err: any) {
      console.error("Failed to load maintenance data:", err);
      setError(err?.message || "Failed to load maintenance operations from server.");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, priorityFilter, domainFilter, selectedId]);

  useEffect(() => {
    fetchWorkOrders();
  }, [fetchWorkOrders]);

  // Fetch full detail whenever selectedId changes
  useEffect(() => {
    if (!selectedId) {
      setSelectedDetail(null);
      return;
    }
    let isMounted = true;
    async function loadDetail() {
      try {
        setDetailLoading(true);
        const detail = await apiClient.getWorkOrderDetail(selectedId!);
        if (isMounted) setSelectedDetail(detail);
      } catch (err: any) {
        console.error("Failed to load work order detail:", err);
      } finally {
        if (isMounted) setDetailLoading(false);
      }
    }
    loadDetail();
    return () => {
      isMounted = false;
    };
  }, [selectedId]);

  // Handle Lifecycle Action Submissions
  const handleLifecycleAction = async () => {
    if (!actionModal) return;
    try {
      setActionInProgress(true);
      setActionError(null);
      const { type, workOrderId } = actionModal;

      if (type === "acknowledge") {
        await apiClient.acknowledgeWorkOrder(workOrderId, actionNotes || undefined);
      } else if (type === "start") {
        await apiClient.startWorkOrder(workOrderId, actionNotes || undefined);
      } else if (type === "complete") {
        if (!actionNotes || actionNotes.trim().length < 3) {
          setActionError("Resolution notes are required to complete maintenance (min 3 chars).");
          setActionInProgress(false);
          return;
        }
        await apiClient.completeWorkOrder(workOrderId, actionNotes.trim());
      } else if (type === "cancel") {
        if (!actionNotes || actionNotes.trim().length < 3) {
          setActionError("Cancellation reason is required (min 3 chars).");
          setActionInProgress(false);
          return;
        }
        await apiClient.cancelWorkOrder(workOrderId, actionNotes.trim());
      }

      setActionModal(null);
      setActionNotes("");
      // Refresh current detail and list
      const updated = await apiClient.getWorkOrderDetail(workOrderId);
      setSelectedDetail(updated);
      await fetchWorkOrders();
    } catch (err: any) {
      setActionError(err?.message || "Lifecycle transition failed. Check requirements.");
    } finally {
      setActionInProgress(false);
    }
  };

  // Handle Create Work Order from Modal
  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createForm.source_reference.trim()) {
      setCreateError("Valid UUID source reference is required.");
      return;
    }
    try {
      setActionInProgress(true);
      setCreateError(null);

      const created = await apiClient.createWorkOrder({
        source_domain: createForm.source_domain,
        source_type: createForm.source_type,
        source_reference: createForm.source_reference.trim(),
        priority: createForm.priority,
      });

      setShowCreateModal(false);
      setCreateForm({
        source_domain: "MACHINE_HEALTH",
        source_type: "RISK_ASSESSMENT",
        source_reference: "",
      });
      setSelectedId(created.id);
      await fetchWorkOrders();
    } catch (err: any) {
      setCreateError(err?.message || "Failed to create work order from source.");
    } finally {
      setActionInProgress(false);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "CRITICAL":
        return "var(--risk-critical)";
      case "HIGH":
        return "var(--risk-elevated)";
      case "MEDIUM":
        return "#EAB308";
      case "LOW":
        return "#3B82F6";
      default:
        return "var(--text-muted)";
    }
  };

  const getStatusBadgeStyle = (status: string) => {
    switch (status) {
      case "OPEN":
        return { bg: "rgba(56, 189, 248, 0.12)", color: "var(--accent-cyan)", border: "rgba(56, 189, 248, 0.3)" };
      case "ACKNOWLEDGED":
        return { bg: "rgba(167, 139, 250, 0.12)", color: "#A78BFA", border: "rgba(167, 139, 250, 0.3)" };
      case "IN_PROGRESS":
        return { bg: "rgba(250, 204, 21, 0.12)", color: "#FACC15", border: "rgba(250, 204, 21, 0.3)" };
      case "COMPLETED":
        return { bg: "rgba(34, 197, 94, 0.12)", color: "var(--risk-normal)", border: "rgba(34, 197, 94, 0.3)" };
      case "CANCELLED":
        return { bg: "rgba(100, 116, 139, 0.12)", color: "#94A3B8", border: "rgba(100, 116, 139, 0.3)" };
      default:
        return { bg: "var(--bg-surface)", color: "var(--text-muted)", border: "var(--border-default)" };
    }
  };

  return (
    <AppShell>
      <PageHeader
        title="Maintenance Workflow & Operations"
        subtitle="Industrial operational workflow connecting verified sensor prognostics and defect vision findings to traceable work items, human reviews, and audit trails."
        breadcrumbs={[{ label: "Operations" }, { label: "Maintenance Work Orders" }]}
        actions={
          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={() => fetchWorkOrders()}
              className="btn btn-secondary"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "8px 14px",
                fontSize: 12,
                fontFamily: "var(--font-mono)",
              }}
              title="Refresh queue"
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
              REFRESH
            </button>
            {canMutate && (
              <button
                onClick={() => setShowCreateModal(true)}
                style={{
                  padding: "8px 16px",
                  backgroundColor: "var(--accent-cyan)",
                  color: "#05070A",
                  borderRadius: "var(--radius-sm)",
                  fontSize: 12,
                  fontWeight: 600,
                  fontFamily: "var(--font-mono)",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  cursor: "pointer",
                  border: "none",
                }}
              >
                <Plus size={15} />
                CREATE RECOMMENDATION
              </button>
            )}
          </div>
        }
      />

      {/* 1. Maintenance KPI Ribbon */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 16,
          marginBottom: 24,
        }}
      >
        <div className="panel" style={{ padding: "16px 20px", borderLeft: "3px solid var(--accent-cyan)" }}>
          <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Open Work Orders
          </div>
          <div style={{ fontSize: 24, fontWeight: 700, fontFamily: "var(--font-mono)", marginTop: 6, color: "var(--accent-cyan)" }}>
            {summary ? summary.open_count : "—"}
          </div>
        </div>

        <div className="panel" style={{ padding: "16px 20px", borderLeft: "3px solid #A78BFA" }}>
          <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Acknowledged
          </div>
          <div style={{ fontSize: 24, fontWeight: 700, fontFamily: "var(--font-mono)", marginTop: 6, color: "#A78BFA" }}>
            {summary ? summary.acknowledged_count : "—"}
          </div>
        </div>

        <div className="panel" style={{ padding: "16px 20px", borderLeft: "3px solid #FACC15" }}>
          <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", textTransform: "uppercase" }}>
            In Progress
          </div>
          <div style={{ fontSize: 24, fontWeight: 700, fontFamily: "var(--font-mono)", marginTop: 6, color: "#FACC15" }}>
            {summary ? summary.in_progress_count : "—"}
          </div>
        </div>

        <div className="panel" style={{ padding: "16px 20px", borderLeft: "3px solid var(--risk-normal)" }}>
          <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Completed Outcomes
          </div>
          <div style={{ fontSize: 24, fontWeight: 700, fontFamily: "var(--font-mono)", marginTop: 6, color: "var(--risk-normal)" }}>
            {summary ? summary.completed_count : "—"}
          </div>
        </div>

        <div className="panel" style={{ padding: "16px 20px", borderLeft: "3px solid var(--risk-critical)" }}>
          <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Critical Priority
          </div>
          <div style={{ fontSize: 24, fontWeight: 700, fontFamily: "var(--font-mono)", marginTop: 6, color: "var(--risk-critical)" }}>
            {summary ? summary.critical_priority_count : "—"}
          </div>
        </div>
      </div>

      {/* 2. Filter Toolbar */}
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
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginRight: 4 }}>
            STATUS:
          </span>
          {["ALL", "OPEN", "ACKNOWLEDGED", "IN_PROGRESS", "COMPLETED", "CANCELLED"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              style={{
                padding: "5px 10px",
                backgroundColor: statusFilter === st ? "var(--accent-cyan-glow)" : "var(--bg-surface)",
                color: statusFilter === st ? "var(--accent-cyan)" : "var(--text-secondary)",
                border: `1px solid ${statusFilter === st ? "var(--accent-cyan)" : "var(--border-default)"}`,
                borderRadius: "var(--radius-sm)",
                fontSize: 11,
                fontWeight: 600,
                fontFamily: "var(--font-mono)",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
            >
              {st}
            </button>
          ))}
        </div>

        {/* Priority & Domain Filters */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>PRIORITY:</span>
            {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((pr) => (
              <button
                key={pr}
                onClick={() => setPriorityFilter(pr)}
                style={{
                  padding: "4px 8px",
                  backgroundColor: priorityFilter === pr ? "rgba(255,255,255,0.08)" : "transparent",
                  color: priorityFilter === pr ? "#FFF" : "var(--text-muted)",
                  border: `1px solid ${priorityFilter === pr ? "var(--border-strong)" : "transparent"}`,
                  borderRadius: "var(--radius-sm)",
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  cursor: "pointer",
                }}
              >
                {pr}
              </button>
            ))}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>DOMAIN:</span>
            {["ALL", "MACHINE_HEALTH", "VISUAL_INSPECTION"].map((dom) => (
              <button
                key={dom}
                onClick={() => setDomainFilter(dom)}
                style={{
                  padding: "4px 8px",
                  backgroundColor: domainFilter === dom ? "rgba(56,189,248,0.12)" : "transparent",
                  color: domainFilter === dom ? "var(--accent-cyan)" : "var(--text-muted)",
                  border: `1px solid ${domainFilter === dom ? "var(--accent-cyan)" : "transparent"}`,
                  borderRadius: "var(--radius-sm)",
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  cursor: "pointer",
                }}
              >
                {dom === "ALL" ? "ALL" : dom === "MACHINE_HEALTH" ? "HEALTH" : "INSPECTION"}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Error or Loading */}
      {error && <ErrorState message={error} onRetry={fetchWorkOrders} />}

      {/* 3. Main Workspace: Queue on Left, Detail Drawer on Right */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: selectedDetail ? "1fr 480px" : "1fr",
          gap: 20,
          alignItems: "start",
        }}
      >
        {/* Left: Work Order Queue */}
        <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
          <div
            style={{
              padding: "14px 20px",
              borderBottom: "1px solid var(--border-default)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              backgroundColor: "rgba(255, 255, 255, 0.02)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Layers size={16} color="var(--accent-cyan)" />
              <span style={{ fontSize: 13, fontWeight: 600, fontFamily: "var(--font-mono)" }}>
                WORK ORDER QUEUE ({workOrders.length})
              </span>
            </div>
            <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
              STRICT DOMAIN SEPARATION ENFORCED
            </span>
          </div>

          {loading ? (
            <div style={{ padding: 24 }}>
              <LoadingSkeleton count={6} />
            </div>
          ) : workOrders.length === 0 ? (
            <div style={{ padding: 32 }}>
              <EmptyState
                icon="database"
                metadataTag="MAINTENANCE OPERATIONS"
                title="No Matching Work Orders"
                description="No maintenance work orders match the selected status, priority, or domain filters. Create a new recommendation or adjust your filters."
              />
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: 12 }}>
                <thead>
                  <tr
                    style={{
                      borderBottom: "1px solid var(--border-default)",
                      backgroundColor: "rgba(0,0,0,0.2)",
                      fontSize: 11,
                      fontFamily: "var(--font-mono)",
                      color: "var(--text-muted)",
                    }}
                  >
                    <th style={{ padding: "10px 16px" }}>PRIORITY</th>
                    <th style={{ padding: "10px 16px" }}>STATUS</th>
                    <th style={{ padding: "10px 16px" }}>DOMAIN / SOURCE</th>
                    <th style={{ padding: "10px 16px" }}>ASSET / SUBJECT</th>
                    <th style={{ padding: "10px 16px" }}>TITLE & REASON</th>
                    <th style={{ padding: "10px 16px" }}>CREATED</th>
                    <th style={{ padding: "10px 16px", textAlign: "right" }}>ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  {workOrders.map((wo) => {
                    const isSelected = selectedId === wo.id;
                    const stStyle = getStatusBadgeStyle(wo.status);
                    return (
                      <tr
                        key={wo.id}
                        onClick={() => setSelectedId(wo.id)}
                        style={{
                          borderBottom: "1px solid var(--border-subtle)",
                          backgroundColor: isSelected ? "rgba(56, 189, 248, 0.08)" : "transparent",
                          cursor: "pointer",
                          transition: "background-color 0.12s ease",
                        }}
                      >
                        {/* Priority Badge */}
                        <td style={{ padding: "12px 16px" }}>
                          <span
                            style={{
                              display: "inline-block",
                              padding: "2px 8px",
                              borderRadius: "var(--radius-sm)",
                              fontSize: 10,
                              fontWeight: 700,
                              fontFamily: "var(--font-mono)",
                              color: getPriorityColor(wo.priority),
                              backgroundColor: "rgba(0,0,0,0.3)",
                              border: `1px solid ${getPriorityColor(wo.priority)}`,
                            }}
                          >
                            {wo.priority}
                          </span>
                        </td>

                        {/* Status Badge */}
                        <td style={{ padding: "12px 16px" }}>
                          <span
                            style={{
                              display: "inline-block",
                              padding: "2px 8px",
                              borderRadius: "var(--radius-sm)",
                              fontSize: 10,
                              fontWeight: 600,
                              fontFamily: "var(--font-mono)",
                              backgroundColor: stStyle.bg,
                              color: stStyle.color,
                              border: `1px solid ${stStyle.border}`,
                            }}
                          >
                            {wo.status}
                          </span>
                        </td>

                        {/* Domain / Source */}
                        <td style={{ padding: "12px 16px" }}>
                          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                            <span
                              style={{
                                fontSize: 10,
                                fontWeight: 700,
                                fontFamily: "var(--font-mono)",
                                color: wo.source_domain === "MACHINE_HEALTH" ? "var(--accent-cyan)" : "#C084FC",
                              }}
                            >
                              {wo.source_domain === "MACHINE_HEALTH" ? "HEALTH" : "INSPECTION"}
                            </span>
                            <span style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                              {wo.source_type}
                            </span>
                          </div>
                        </td>

                        {/* Machine / Target */}
                        <td style={{ padding: "12px 16px" }}>
                          <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600, color: "var(--text-primary)" }}>
                            {wo.machine_id || "Metal Nut Specimen"}
                          </span>
                        </td>

                        {/* Title & Reason */}
                        <td style={{ padding: "12px 16px", maxWidth: 300 }}>
                          <div
                            style={{
                              fontWeight: 600,
                              color: "var(--text-primary)",
                              whiteSpace: "nowrap",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                            }}
                          >
                            {wo.title}
                          </div>
                          <div
                            style={{
                              fontSize: 11,
                              color: "var(--text-muted)",
                              whiteSpace: "nowrap",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              marginTop: 2,
                            }}
                          >
                            {wo.reason}
                          </div>
                        </td>

                        {/* Created */}
                        <td style={{ padding: "12px 16px", whiteSpace: "nowrap", color: "var(--text-muted)", fontSize: 11, fontFamily: "var(--font-mono)" }}>
                          {new Date(wo.created_at).toLocaleDateString()}{" "}
                          {new Date(wo.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </td>

                        {/* View Action */}
                        <td style={{ padding: "12px 16px", textAlign: "right" }}>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedId(wo.id);
                            }}
                            className="btn btn-secondary"
                            style={{ padding: "4px 8px", fontSize: 11, fontFamily: "var(--font-mono)" }}
                          >
                            VIEW
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right: Work Order Detail Panel */}
        {selectedDetail && (
          <div className="panel" style={{ padding: 0, position: "sticky", top: 80 }}>
            {/* Detail Header */}
            <div
              style={{
                padding: "16px 20px",
                borderBottom: "1px solid var(--border-default)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                backgroundColor: "rgba(255, 255, 255, 0.02)",
              }}
            >
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <span
                    style={{
                      padding: "2px 8px",
                      borderRadius: "var(--radius-sm)",
                      fontSize: 10,
                      fontWeight: 700,
                      fontFamily: "var(--font-mono)",
                      color: getPriorityColor(selectedDetail.priority),
                      border: `1px solid ${getPriorityColor(selectedDetail.priority)}`,
                      backgroundColor: "rgba(0,0,0,0.3)",
                    }}
                  >
                    {selectedDetail.priority}
                  </span>
                  <span
                    style={{
                      padding: "2px 8px",
                      borderRadius: "var(--radius-sm)",
                      fontSize: 10,
                      fontWeight: 600,
                      fontFamily: "var(--font-mono)",
                      ...getStatusBadgeStyle(selectedDetail.status),
                    }}
                  >
                    {selectedDetail.status}
                  </span>
                  <span
                    style={{
                      fontSize: 10,
                      fontFamily: "var(--font-mono)",
                      color: selectedDetail.source_domain === "MACHINE_HEALTH" ? "var(--accent-cyan)" : "#C084FC",
                    }}
                  >
                    {selectedDetail.source_domain}
                  </span>
                </div>
                <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)" }}>
                  {selectedDetail.title}
                </div>
                <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginTop: 4 }}>
                  WO ID: {selectedDetail.id}
                </div>
              </div>
              <button
                onClick={() => setSelectedDetail(null)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  padding: 4,
                }}
              >
                <X size={18} />
              </button>
            </div>

            {/* Detail Body */}
            <div style={{ padding: 20, maxHeight: "calc(100vh - 220px)", overflowY: "auto" }}>
              {/* Mandatory Non-Autonomous Safety Banner */}
              <div
                style={{
                  padding: "10px 14px",
                  backgroundColor: "rgba(56, 189, 248, 0.06)",
                  border: "1px solid rgba(56, 189, 248, 0.2)",
                  borderRadius: "var(--radius-sm)",
                  fontSize: 11,
                  color: "var(--text-secondary)",
                  marginBottom: 16,
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 8,
                }}
              >
                <ShieldAlert size={16} color="var(--accent-cyan)" style={{ flexShrink: 0, marginTop: 2 }} />
                <span>
                  <strong>HUMAN DECISION-SUPPORT WORKFLOW:</strong> This work item is derived deterministically from validated evidence. MachIntel does not issue direct machinery actuator commands or trigger autonomous shutdowns.
                </span>
              </div>

              {/* Recommended Action Card */}
              <div
                style={{
                  padding: "14px 16px",
                  backgroundColor: "rgba(234, 179, 8, 0.08)",
                  border: "1px solid rgba(234, 179, 8, 0.3)",
                  borderRadius: "var(--radius-sm)",
                  marginBottom: 16,
                }}
              >
                <div style={{ fontSize: 11, fontWeight: 700, fontFamily: "var(--font-mono)", color: "#FACC15", marginBottom: 4 }}>
                  RECOMMENDED ACTION
                </div>
                <div style={{ fontSize: 12, lineHeight: 1.5, color: "var(--text-primary)" }}>
                  {selectedDetail.recommended_action}
                </div>
              </div>

              {/* Factual Evidence Reason */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 11, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 4 }}>
                  GROUND TRUTH EVIDENCE REASON
                </div>
                <div
                  style={{
                    fontSize: 12,
                    lineHeight: 1.5,
                    color: "var(--text-secondary)",
                    backgroundColor: "rgba(0,0,0,0.2)",
                    padding: "10px 12px",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--border-default)",
                  }}
                >
                  {selectedDetail.reason}
                </div>
              </div>

              {/* Context Snapshot at Creation */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 11, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 6 }}>
                  EVIDENCE SNAPSHOT AT CREATION
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  {selectedDetail.source_domain === "MACHINE_HEALTH" ? (
                    <>
                      <div className="panel" style={{ padding: "8px 12px" }}>
                        <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>PREDICTED RUL</div>
                        <div style={{ fontSize: 16, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-cyan)" }}>
                          {selectedDetail.predicted_rul_at_creation !== null && selectedDetail.predicted_rul_at_creation !== undefined
                            ? `${selectedDetail.predicted_rul_at_creation.toFixed(1)} cycles`
                            : "—"}
                        </div>
                      </div>
                      <div className="panel" style={{ padding: "8px 12px" }}>
                        <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>HEALTH INDEX</div>
                        <div style={{ fontSize: 16, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>
                          {selectedDetail.health_index_at_creation !== null && selectedDetail.health_index_at_creation !== undefined
                            ? selectedDetail.health_index_at_creation.toFixed(3)
                            : "—"}
                        </div>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="panel" style={{ padding: "8px 12px" }}>
                        <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>ANOMALY SCORE</div>
                        <div style={{ fontSize: 16, fontWeight: 700, fontFamily: "var(--font-mono)", color: "#C084FC" }}>
                          {selectedDetail.anomaly_score_at_creation !== null && selectedDetail.anomaly_score_at_creation !== undefined
                            ? selectedDetail.anomaly_score_at_creation.toFixed(4)
                            : "—"}
                        </div>
                      </div>
                      <div className="panel" style={{ padding: "8px 12px" }}>
                        <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>DECISION</div>
                        <div style={{ fontSize: 16, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--risk-critical)" }}>
                          DEFECT
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Resolution Notes (if completed or cancelled) */}
              {selectedDetail.resolution_notes && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 4 }}>
                    OPERATOR RESOLUTION / OUTCOME NOTES
                  </div>
                  <div
                    style={{
                      padding: "10px 12px",
                      backgroundColor: "rgba(34, 197, 94, 0.08)",
                      border: "1px solid rgba(34, 197, 94, 0.3)",
                      borderRadius: "var(--radius-sm)",
                      fontSize: 12,
                      color: "var(--text-primary)",
                    }}
                  >
                    {selectedDetail.resolution_notes}
                  </div>
                </div>
              )}

              {/* 4. Lifecycle Action Controls */}
              <div style={{ marginBottom: 20, paddingTop: 10, borderTop: "1px solid var(--border-default)" }}>
                <div style={{ fontSize: 11, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 10 }}>
                  WORKFLOW TRANSITION CONTROLS
                </div>

                {!canMutate ? (
                  <div style={{ fontSize: 11, color: "var(--text-muted)", fontStyle: "italic" }}>
                    Viewer role: Read-only access. Login as Operator or Admin to execute transitions.
                  </div>
                ) : selectedDetail.status === "COMPLETED" || selectedDetail.status === "CANCELLED" ? (
                  <div style={{ fontSize: 11, color: "var(--text-muted)", fontStyle: "italic" }}>
                    Work order is in terminal state ({selectedDetail.status}). No further transitions allowed.
                  </div>
                ) : (
                  <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                    {selectedDetail.status === "OPEN" && (
                      <button
                        onClick={() => setActionModal({ type: "acknowledge", workOrderId: selectedDetail.id })}
                        className="btn btn-primary"
                        style={{ padding: "6px 12px", fontSize: 11, fontFamily: "var(--font-mono)" }}
                      >
                        ACKNOWLEDGE WORK ORDER
                      </button>
                    )}

                    {selectedDetail.status === "ACKNOWLEDGED" && (
                      <button
                        onClick={() => setActionModal({ type: "start", workOrderId: selectedDetail.id })}
                        className="btn btn-primary"
                        style={{ padding: "6px 12px", fontSize: 11, fontFamily: "var(--font-mono)" }}
                      >
                        START EXECUTION
                      </button>
                    )}

                    {selectedDetail.status === "IN_PROGRESS" && (
                      <button
                        onClick={() => setActionModal({ type: "complete", workOrderId: selectedDetail.id })}
                        style={{
                          padding: "6px 12px",
                          fontSize: 11,
                          fontFamily: "var(--font-mono)",
                          fontWeight: 600,
                          backgroundColor: "var(--risk-normal)",
                          color: "#05070A",
                          borderRadius: "var(--radius-sm)",
                          border: "none",
                          cursor: "pointer",
                        }}
                      >
                        COMPLETE & RECORD OUTCOME
                      </button>
                    )}

                    <button
                      onClick={() => setActionModal({ type: "cancel", workOrderId: selectedDetail.id })}
                      className="btn btn-secondary"
                      style={{ padding: "6px 12px", fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--risk-critical)" }}
                    >
                      CANCEL
                    </button>
                  </div>
                )}
              </div>

              {/* 5. Immutable Event History Timeline */}
              <div style={{ borderTop: "1px solid var(--border-default)", paddingTop: 16 }}>
                <div style={{ fontSize: 11, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 12 }}>
                  IMMUTABLE AUDIT TRAIL ({selectedDetail.events?.length || 0})
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {selectedDetail.events?.map((ev) => (
                    <div
                      key={ev.id}
                      style={{
                        display: "flex",
                        gap: 12,
                        alignItems: "flex-start",
                        fontSize: 11,
                        borderLeft: "2px solid var(--border-default)",
                        paddingLeft: 12,
                      }}
                    >
                      <div style={{ flex: 1 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                          <span style={{ fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>
                            {ev.event_type}
                          </span>
                          <span style={{ color: "var(--text-muted)" }}>→</span>
                          <span style={{ fontFamily: "var(--font-mono)", color: "var(--accent-cyan)" }}>
                            {ev.to_status}
                          </span>
                        </div>
                        {ev.notes && (
                          <div style={{ color: "var(--text-secondary)", fontSize: 11, marginTop: 2 }}>
                            {ev.notes}
                          </div>
                        )}
                        <div style={{ color: "var(--text-muted)", fontSize: 10, fontFamily: "var(--font-mono)", marginTop: 4 }}>
                          {new Date(ev.created_at).toLocaleString()}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Action Transition Modal */}
      {actionModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0,0,0,0.75)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: 20,
          }}
        >
          <div className="panel" style={{ width: "100%", maxWidth: 450, padding: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <div style={{ fontSize: 16, fontWeight: 700, fontFamily: "var(--font-mono)" }}>
                {actionModal.type === "acknowledge"
                  ? "Acknowledge Work Order"
                  : actionModal.type === "start"
                  ? "Start Maintenance Execution"
                  : actionModal.type === "complete"
                  ? "Record Maintenance Outcome"
                  : "Cancel Work Order"}
              </div>
              <button
                onClick={() => {
                  setActionModal(null);
                  setActionNotes("");
                  setActionError(null);
                }}
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
              >
                <X size={18} />
              </button>
            </div>

            {actionError && (
              <div
                style={{
                  padding: "8px 12px",
                  backgroundColor: "rgba(239, 68, 68, 0.1)",
                  border: "1px solid var(--risk-critical)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--risk-critical)",
                  fontSize: 12,
                  marginBottom: 12,
                }}
              >
                {actionError}
              </div>
            )}

            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 16 }}>
              {actionModal.type === "complete"
                ? "Document the verified physical inspection outcome and any corrective measures performed. This will be preserved in the authentic audit log."
                : actionModal.type === "cancel"
                ? "State the operational justification for cancelling this work item."
                : "Add optional shift notes or operator remarks for this transition."}
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 6 }}>
                {actionModal.type === "complete"
                  ? "RESOLUTION NOTES (REQUIRED)*"
                  : actionModal.type === "cancel"
                  ? "CANCELLATION REASON (REQUIRED)*"
                  : "NOTES (OPTIONAL)"}
              </label>
              <textarea
                value={actionNotes}
                onChange={(e) => setActionNotes(e.target.value)}
                placeholder={
                  actionModal.type === "complete"
                    ? "e.g. Combustor liner inspected. Replaced sensor connector #2 and recalibrated baseline."
                    : actionModal.type === "cancel"
                    ? "e.g. False alarm confirmed after physical gauge cross-check."
                    : "Enter transition remarks..."
                }
                rows={4}
                style={{
                  width: "100%",
                  padding: 10,
                  backgroundColor: "rgba(0,0,0,0.3)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--text-primary)",
                  fontSize: 12,
                  fontFamily: "var(--font-sans)",
                }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button
                type="button"
                onClick={() => {
                  setActionModal(null);
                  setActionNotes("");
                  setActionError(null);
                }}
                className="btn btn-secondary"
                style={{ padding: "8px 14px", fontSize: 12 }}
              >
                CANCEL
              </button>
              <button
                type="button"
                disabled={actionInProgress}
                onClick={handleLifecycleAction}
                className="btn btn-primary"
                style={{ padding: "8px 16px", fontSize: 12, fontFamily: "var(--font-mono)" }}
              >
                {actionInProgress ? "RECORDING..." : "CONFIRM TRANSITION"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Recommendation Modal */}
      {showCreateModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0,0,0,0.75)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: 20,
          }}
        >
          <div className="panel" style={{ width: "100%", maxWidth: 500, padding: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <div style={{ fontSize: 16, fontWeight: 700, fontFamily: "var(--font-mono)" }}>
                Draft Maintenance Recommendation
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
              >
                <X size={18} />
              </button>
            </div>

            {createError && (
              <div
                style={{
                  padding: "8px 12px",
                  backgroundColor: "rgba(239, 68, 68, 0.1)",
                  border: "1px solid var(--risk-critical)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--risk-critical)",
                  fontSize: 12,
                  marginBottom: 14,
                }}
              >
                {createError}
              </div>
            )}

            <form onSubmit={handleCreateSubmit}>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: "block", fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 6 }}>
                  SOURCE DOMAIN
                </label>
                <select
                  value={createForm.source_domain}
                  onChange={(e) => {
                    const dom = e.target.value as MaintenanceSourceDomain;
                    setCreateForm({
                      ...createForm,
                      source_domain: dom,
                      source_type: dom === "MACHINE_HEALTH" ? "RISK_ASSESSMENT" : "INSPECTION_RESULT",
                    });
                  }}
                  style={{
                    width: "100%",
                    padding: 8,
                    backgroundColor: "rgba(0,0,0,0.3)",
                    border: "1px solid var(--border-default)",
                    borderRadius: "var(--radius-sm)",
                    color: "var(--text-primary)",
                    fontSize: 12,
                  }}
                >
                  <option value="MACHINE_HEALTH">Machine Health (C-MAPSS FD001)</option>
                  <option value="VISUAL_INSPECTION">Visual Inspection (MVTec AD metal_nut)</option>
                </select>
              </div>

              <div style={{ marginBottom: 14 }}>
                <label style={{ display: "block", fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 6 }}>
                  SOURCE TYPE
                </label>
                <select
                  value={createForm.source_type}
                  onChange={(e) => setCreateForm({ ...createForm, source_type: e.target.value as MaintenanceSourceType })}
                  style={{
                    width: "100%",
                    padding: 8,
                    backgroundColor: "rgba(0,0,0,0.3)",
                    border: "1px solid var(--border-default)",
                    borderRadius: "var(--radius-sm)",
                    color: "var(--text-primary)",
                    fontSize: 12,
                  }}
                >
                  {createForm.source_domain === "MACHINE_HEALTH" ? (
                    <>
                      <option value="RISK_ASSESSMENT">Risk Assessment</option>
                      <option value="ALERT">Active Alert</option>
                    </>
                  ) : (
                    <option value="INSPECTION_RESULT">Defect Inspection Result</option>
                  )}
                </select>
              </div>

              <div style={{ marginBottom: 14 }}>
                <label style={{ display: "block", fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 6 }}>
                  SOURCE REFERENCE UUID*
                </label>
                <input
                  type="text"
                  placeholder="e.g. 3fa85f64-5717-4562-b3fc-2c963f66afa6"
                  value={createForm.source_reference}
                  onChange={(e) => setCreateForm({ ...createForm, source_reference: e.target.value })}
                  style={{
                    width: "100%",
                    padding: 8,
                    backgroundColor: "rgba(0,0,0,0.3)",
                    border: "1px solid var(--border-default)",
                    borderRadius: "var(--radius-sm)",
                    color: "var(--text-primary)",
                    fontSize: 12,
                    fontFamily: "var(--font-mono)",
                  }}
                />
                <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 4 }}>
                  The UUID of an authentic {createForm.source_type} record. Arbitrary references are rejected.
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 20 }}>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="btn btn-secondary"
                  style={{ padding: "8px 14px", fontSize: 12 }}
                >
                  CANCEL
                </button>
                <button
                  type="submit"
                  disabled={actionInProgress}
                  className="btn btn-primary"
                  style={{ padding: "8px 16px", fontSize: 12, fontFamily: "var(--font-mono)" }}
                >
                  {actionInProgress ? "VALIDATING..." : "GENERATE WORK ORDER"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppShell>
  );
}
