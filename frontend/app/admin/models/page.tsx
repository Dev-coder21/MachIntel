"use client";

import React, { useEffect, useState, useCallback } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { apiClient } from "@/lib/api-client";
import {
  ModelEvaluationItem,
  ModelGateReport,
  ModelIntegrityReport,
  ModelMonitoringSummary,
  ModelPromotionItem,
  ModelRegistryItem,
  ModelRegistryListResponse,
} from "@/types/model";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  BarChart2,
  CheckCircle,
  Cpu,
  Eye,
  FileCheck,
  FileText,
  GitBranch,
  Layers,
  Lock,
  RefreshCw,
  RotateCw,
  Shield,
  ShieldAlert,
  ShieldCheck,
  X,
  Zap,
} from "lucide-react";

export default function ModelLifecyclePage() {
  const [models, setModels] = useState<ModelRegistryItem[]>([]);
  const [activeRulId, setActiveRulId] = useState<string | null>(null);
  const [activeCvId, setActiveCvId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [domainFilter, setDomainFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [userRole, setUserRole] = useState<string>("VIEWER");
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Selected Model Detail
  const [selectedModel, setSelectedModel] = useState<ModelRegistryItem | null>(null);
  const [evaluations, setEvaluations] = useState<ModelEvaluationItem[]>([]);
  const [promotions, setPromotions] = useState<ModelPromotionItem[]>([]);
  const [integrityReport, setIntegrityReport] = useState<ModelIntegrityReport | null>(null);
  const [gatesReport, setGatesReport] = useState<ModelGateReport | null>(null);
  const [monitoringSummary, setMonitoringSummary] = useState<ModelMonitoringSummary | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Promotion / Retirement Modal
  const [actionModal, setActionModal] = useState<"promote" | "retire" | null>(null);
  const [actionReason, setActionReason] = useState("");
  const [actionSubmitting, setActionSubmitting] = useState(false);

  const fetchModels = useCallback(async () => {
    try {
      const res = await apiClient.getModels({
        domain: domainFilter || undefined,
        status: statusFilter || undefined,
      });
      setModels(res.items);
      setActiveRulId(res.active_machine_health_model_id || null);
      setActiveCvId(res.active_visual_inspection_model_id || null);
    } catch (err: any) {
      console.error("Failed to load models:", err);
      setErrorMessage("Failed to load model registry from server.");
    } finally {
      setLoading(false);
    }
  }, [domainFilter, statusFilter]);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("user");
      if (stored) {
        const u = JSON.parse(stored);
        if (u && u.role) setUserRole(u.role);
      }
    } catch (e) {
      // Ignore
    }

    fetchModels();
  }, [fetchModels]);

  const loadModelDetails = async (model: ModelRegistryItem) => {
    setSelectedModel(model);
    setLoadingDetail(true);
    setIntegrityReport(null);
    setGatesReport(null);
    setActionMessage(null);
    setErrorMessage(null);

    try {
      const [evalsRes, promosRes, integRes, gatesRes, monitorRes] = await Promise.all([
        apiClient.getModelEvaluations(model.model_id),
        apiClient.getModelPromotions(model.model_id),
        apiClient.getModelIntegrity(model.model_id),
        apiClient.getModelGates(model.model_id),
        apiClient.getModelMonitoringSummary(model.domain),
      ]);
      setEvaluations(evalsRes);
      setPromotions(promosRes);
      setIntegrityReport(integRes);
      setGatesReport(gatesRes);
      setMonitoringSummary(monitorRes);
    } catch (err: any) {
      console.error("Error loading model details:", err);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleVerifyIntegrity = async (modelId: string) => {
    try {
      const rep = await apiClient.verifyModelIntegrity(modelId);
      setIntegrityReport(rep);
      if (rep.is_valid) {
        setActionMessage(`Cryptographic SHA-256 verification PASSED for ${modelId}. Artifact match verified.`);
      } else {
        setErrorMessage(`INTEGRITY FAILURE: Artifact checksum mismatch or file missing!`);
      }
    } catch (err: any) {
      setErrorMessage(`Integrity verification failed: ${err.message || "Unknown error"}`);
    }
  };

  const handleExecutePromotion = async () => {
    if (!selectedModel || !actionReason) return;
    setActionSubmitting(true);
    setActionMessage(null);
    setErrorMessage(null);

    try {
      if (actionModal === "promote") {
        const updated = await apiClient.promoteModel(selectedModel.model_id, actionReason);
        setActionMessage(`Model ${updated.model_id} successfully promoted to PROMOTED status.`);
      } else if (actionModal === "retire") {
        const updated = await apiClient.retireModel(selectedModel.model_id, actionReason);
        setActionMessage(`Model ${updated.model_id} successfully demoted to RETIRED status.`);
      }
      setActionModal(null);
      setActionReason("");
      await fetchModels();
      // Reload detail
      const refreshedModel = await apiClient.getModel(selectedModel.model_id);
      loadModelDetails(refreshedModel);
    } catch (err: any) {
      setErrorMessage(`Action failed: ${err.message || "Gate violation or unauthorized"}`);
    } finally {
      setActionSubmitting(false);
    }
  };

  const isAdmin = userRole === "ADMIN";

  return (
    <AppShell>
      <div style={{ padding: "28px 36px", display: "flex", flexDirection: "column", gap: 24, maxWidth: 1400 }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <GitBranch size={22} color="var(--accent-cyan)" />
              <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.02em", color: "var(--text-primary)" }}>
                MODEL LIFECYCLE & REGISTRY
              </h1>
              <span
                style={{
                  fontSize: 10,
                  fontFamily: "var(--font-mono)",
                  padding: "2px 8px",
                  borderRadius: 4,
                  backgroundColor: "rgba(0, 229, 255, 0.1)",
                  color: "var(--accent-cyan)",
                  border: "1px solid rgba(0, 229, 255, 0.3)",
                }}
              >
                PHASE 14 MLOPS
              </span>
            </div>
            <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 4 }}>
              Defensible, local-first model lifecycle management: deterministic promotion gates, SHA-256 integrity verification, and reproducible manifests.
            </p>
          </div>

          <button
            onClick={() => fetchModels()}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 14px",
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              color: "var(--text-secondary)",
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            <RefreshCw size={14} />
            <span>Refresh Registry</span>
          </button>
        </div>

        {/* Notifications */}
        {actionMessage && (
          <div
            style={{
              padding: "12px 16px",
              backgroundColor: "rgba(0, 229, 255, 0.08)",
              border: "1px solid var(--accent-cyan)",
              borderRadius: 6,
              display: "flex",
              alignItems: "center",
              gap: 10,
              color: "var(--accent-cyan)",
              fontSize: 13,
            }}
          >
            <CheckCircle size={16} />
            <span>{actionMessage}</span>
          </div>
        )}

        {errorMessage && (
          <div
            style={{
              padding: "12px 16px",
              backgroundColor: "rgba(255, 23, 68, 0.08)",
              border: "1px solid var(--risk-critical)",
              borderRadius: 6,
              display: "flex",
              alignItems: "center",
              gap: 10,
              color: "var(--risk-critical)",
              fontSize: 13,
            }}
          >
            <AlertCircle size={16} />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Top KPI Ribbon */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
          {/* Active RUL Model */}
          <div
            style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              padding: 16,
              display: "flex",
              flexDirection: "column",
              gap: 6,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-muted)", fontSize: 11, fontFamily: "var(--font-mono)" }}>
              <Zap size={14} color="var(--accent-cyan)" />
              <span>ACTIVE RUL MODEL</span>
            </div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
              {activeRulId || "NONE"}
            </div>
            <div style={{ fontSize: 11, color: "var(--risk-normal)", display: "flex", alignItems: "center", gap: 4 }}>
              <ShieldCheck size={12} />
              <span>Domain: MACHINE_HEALTH</span>
            </div>
          </div>

          {/* Active Vision Model */}
          <div
            style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              padding: 16,
              display: "flex",
              flexDirection: "column",
              gap: 6,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-muted)", fontSize: 11, fontFamily: "var(--font-mono)" }}>
              <Eye size={14} color="var(--accent-cyan)" />
              <span>ACTIVE VISION MODEL</span>
            </div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
              {activeCvId || "NONE"}
            </div>
            <div style={{ fontSize: 11, color: "var(--risk-normal)", display: "flex", alignItems: "center", gap: 4 }}>
              <ShieldCheck size={12} />
              <span>Domain: VISUAL_INSPECTION</span>
            </div>
          </div>

          {/* Total Registered Artifacts */}
          <div
            style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              padding: 16,
              display: "flex",
              flexDirection: "column",
              gap: 6,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-muted)", fontSize: 11, fontFamily: "var(--font-mono)" }}>
              <Layers size={14} color="var(--accent-cyan)" />
              <span>REGISTERED ARTIFACTS</span>
            </div>
            <div style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
              {models.length} Models
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
              Storage: storage/models/ (Local FS)
            </div>
          </div>

          {/* Governance Mode */}
          <div
            style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              padding: 16,
              display: "flex",
              flexDirection: "column",
              gap: 6,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-muted)", fontSize: 11, fontFamily: "var(--font-mono)" }}>
              <Shield size={14} color="var(--accent-cyan)" />
              <span>GOVERNANCE POLICY</span>
            </div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "var(--risk-normal)", fontFamily: "var(--font-mono)" }}>
              DETERMINISTIC GATES
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
              Zero Online Retraining • No Cloud
            </div>
          </div>
        </div>

        {/* Filters and Controls */}
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          {/* Domain Filter */}
          <div style={{ display: "flex", gap: 4 }}>
            {[
              { label: "ALL DOMAINS", value: "" },
              { label: "MACHINE HEALTH (RUL)", value: "MACHINE_HEALTH" },
              { label: "VISUAL INSPECTION (CV)", value: "VISUAL_INSPECTION" },
            ].map((tab) => (
              <button
                key={tab.value}
                onClick={() => setDomainFilter(tab.value)}
                style={{
                  padding: "6px 12px",
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                  border: domainFilter === tab.value ? "1px solid var(--accent-cyan)" : "1px solid var(--border-subtle)",
                  backgroundColor: domainFilter === tab.value ? "rgba(0, 229, 255, 0.1)" : "var(--bg-surface)",
                  color: domainFilter === tab.value ? "var(--accent-cyan)" : "var(--text-muted)",
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div style={{ width: 1, height: 20, backgroundColor: "var(--border-subtle)" }} />

          {/* Status Filter */}
          <div style={{ display: "flex", gap: 4 }}>
            {[
              { label: "ALL STATUSES", value: "" },
              { label: "PROMOTED", value: "PROMOTED" },
              { label: "EVALUATED", value: "EVALUATED" },
              { label: "CANDIDATE", value: "CANDIDATE" },
              { label: "RETIRED", value: "RETIRED" },
            ].map((st) => (
              <button
                key={st.value}
                onClick={() => setStatusFilter(st.value)}
                style={{
                  padding: "6px 12px",
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                  border: statusFilter === st.value ? "1px solid var(--accent-cyan)" : "1px solid var(--border-subtle)",
                  backgroundColor: statusFilter === st.value ? "rgba(0, 229, 255, 0.1)" : "var(--bg-surface)",
                  color: statusFilter === st.value ? "var(--accent-cyan)" : "var(--text-muted)",
                }}
              >
                {st.label}
              </button>
            ))}
          </div>
        </div>

        {/* Models Table */}
        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-md)",
            overflow: "hidden",
          }}
        >
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr
                style={{
                  backgroundColor: "rgba(255, 255, 255, 0.02)",
                  borderBottom: "1px solid var(--border-subtle)",
                  color: "var(--text-muted)",
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                  textAlign: "left",
                }}
              >
                <th style={{ padding: "12px 16px" }}>MODEL IDENTIFIER</th>
                <th style={{ padding: "12px 16px" }}>DOMAIN</th>
                <th style={{ padding: "12px 16px" }}>ALGORITHM / FAMILY</th>
                <th style={{ padding: "12px 16px" }}>LIFECYCLE STATE</th>
                <th style={{ padding: "12px 16px" }}>ACTIVE SERVING</th>
                <th style={{ padding: "12px 16px" }}>SHA-256 INTEGRITY</th>
                <th style={{ padding: "12px 16px", textAlign: "right" }}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} style={{ padding: 32, textAlign: "center", color: "var(--text-muted)" }}>
                    Loading model registry...
                  </td>
                </tr>
              ) : models.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: 32, textAlign: "center", color: "var(--text-muted)" }}>
                    No models registered matching the selected criteria.
                  </td>
                </tr>
              ) : (
                models.map((m) => (
                  <tr
                    key={m.model_id}
                    style={{
                      borderBottom: "1px solid var(--border-subtle)",
                      backgroundColor: selectedModel?.model_id === m.model_id ? "rgba(0, 229, 255, 0.05)" : "transparent",
                      transition: "background-color 0.15s ease",
                    }}
                  >
                    <td style={{ padding: "14px 16px", fontFamily: "var(--font-mono)", fontWeight: 600, color: "var(--text-primary)" }}>
                      <div>{m.model_id}</div>
                      <div style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 400 }}>{m.model_name}</div>
                    </td>
                    <td style={{ padding: "14px 16px" }}>
                      <span
                        style={{
                          fontSize: 10,
                          fontFamily: "var(--font-mono)",
                          padding: "3px 8px",
                          borderRadius: 4,
                          backgroundColor: m.domain === "MACHINE_HEALTH" ? "rgba(0, 229, 255, 0.1)" : "rgba(255, 171, 0, 0.1)",
                          color: m.domain === "MACHINE_HEALTH" ? "var(--accent-cyan)" : "var(--risk-watch)",
                          border: `1px solid ${m.domain === "MACHINE_HEALTH" ? "rgba(0, 229, 255, 0.3)" : "rgba(255, 171, 0, 0.3)"}`,
                        }}
                      >
                        {m.domain}
                      </span>
                    </td>
                    <td style={{ padding: "14px 16px" }}>
                      <div style={{ fontWeight: 500, color: "var(--text-secondary)" }}>{m.algorithm}</div>
                      <div style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                        {m.framework} • {m.task}
                      </div>
                    </td>
                    <td style={{ padding: "14px 16px" }}>
                      <span
                        style={{
                          fontSize: 10,
                          fontFamily: "var(--font-mono)",
                          fontWeight: 700,
                          padding: "3px 8px",
                          borderRadius: 4,
                          backgroundColor:
                            m.status === "PROMOTED"
                              ? "rgba(0, 230, 118, 0.15)"
                              : m.status === "EVALUATED"
                              ? "rgba(0, 229, 255, 0.1)"
                              : m.status === "CANDIDATE"
                              ? "rgba(255, 171, 0, 0.1)"
                              : "rgba(255, 255, 255, 0.05)",
                          color:
                            m.status === "PROMOTED"
                              ? "var(--risk-normal)"
                              : m.status === "EVALUATED"
                              ? "var(--accent-cyan)"
                              : m.status === "CANDIDATE"
                              ? "var(--risk-watch)"
                              : "var(--text-muted)",
                          border: `1px solid ${
                            m.status === "PROMOTED"
                              ? "var(--risk-normal)"
                              : m.status === "EVALUATED"
                              ? "rgba(0, 229, 255, 0.3)"
                              : "var(--border-subtle)"
                          }`,
                        }}
                      >
                        {m.status}
                      </span>
                    </td>
                    <td style={{ padding: "14px 16px" }}>
                      {m.is_active ? (
                        <div style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--risk-normal)", fontSize: 12, fontWeight: 600 }}>
                          <CheckCircle size={14} />
                          <span>PRODUCTION</span>
                        </div>
                      ) : (
                        <span style={{ color: "var(--text-muted)", fontSize: 12 }}>Standby</span>
                      )}
                    </td>
                    <td style={{ padding: "14px 16px", fontFamily: "var(--font-mono)", fontSize: 11 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--text-secondary)" }}>
                        <ShieldCheck size={14} color="var(--risk-normal)" />
                        <span>{m.artifact_sha256 ? `${m.artifact_sha256.slice(0, 12)}...` : "None"}</span>
                      </div>
                      <div style={{ fontSize: 10, color: "var(--text-muted)" }}>
                        {m.artifact_size_bytes ? `${(m.artifact_size_bytes / 1024 / 1024).toFixed(2)} MB` : "N/A"}
                      </div>
                    </td>
                    <td style={{ padding: "14px 16px", textAlign: "right" }}>
                      <button
                        onClick={() => loadModelDetails(m)}
                        style={{
                          padding: "6px 12px",
                          backgroundColor: selectedModel?.model_id === m.model_id ? "var(--accent-cyan)" : "rgba(255, 255, 255, 0.05)",
                          color: selectedModel?.model_id === m.model_id ? "#000" : "var(--text-primary)",
                          border: "1px solid var(--border-subtle)",
                          borderRadius: 4,
                          fontSize: 12,
                          cursor: "pointer",
                          fontWeight: 500,
                        }}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Selected Model Detail Panel */}
        {selectedModel && (
          <div
            style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              padding: 24,
              display: "flex",
              flexDirection: "column",
              gap: 20,
            }}
          >
            {/* Header of Detail */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <h2 style={{ fontSize: 18, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>
                    {selectedModel.model_id}
                  </h2>
                  <span
                    style={{
                      fontSize: 11,
                      fontFamily: "var(--font-mono)",
                      padding: "2px 8px",
                      borderRadius: 4,
                      backgroundColor: selectedModel.is_active ? "rgba(0, 230, 118, 0.15)" : "rgba(255, 255, 255, 0.05)",
                      color: selectedModel.is_active ? "var(--risk-normal)" : "var(--text-muted)",
                      border: `1px solid ${selectedModel.is_active ? "var(--risk-normal)" : "var(--border-subtle)"}`,
                    }}
                  >
                    {selectedModel.status}
                  </span>
                </div>
                <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
                  {selectedModel.description || selectedModel.model_name}
                </p>
              </div>

              {/* Action Buttons */}
              <div style={{ display: "flex", gap: 10 }}>
                <button
                  onClick={() => handleVerifyIntegrity(selectedModel.model_id)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "8px 14px",
                    backgroundColor: "var(--bg-app)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: 4,
                    color: "var(--text-primary)",
                    fontSize: 12,
                    cursor: "pointer",
                  }}
                >
                  <ShieldCheck size={14} color="var(--accent-cyan)" />
                  <span>Verify SHA-256</span>
                </button>

                {isAdmin && !selectedModel.is_active && (
                  <button
                    onClick={() => {
                      setActionModal("promote");
                      setActionReason("");
                    }}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      padding: "8px 14px",
                      backgroundColor: "var(--accent-cyan)",
                      border: "none",
                      borderRadius: 4,
                      color: "#000",
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    <ArrowRight size={14} />
                    <span>Promote Model</span>
                  </button>
                )}

                {isAdmin && selectedModel.is_active && (
                  <button
                    onClick={() => {
                      setActionModal("retire");
                      setActionReason("");
                    }}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      padding: "8px 14px",
                      backgroundColor: "rgba(255, 23, 68, 0.15)",
                      border: "1px solid var(--risk-critical)",
                      borderRadius: 4,
                      color: "var(--risk-critical)",
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    <ShieldAlert size={14} />
                    <span>Retire From Production</span>
                  </button>
                )}

                <button
                  onClick={() => setSelectedModel(null)}
                  style={{
                    backgroundColor: "transparent",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    padding: 4,
                  }}
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {loadingDetail ? (
              <div style={{ padding: 24, textAlign: "center", color: "var(--text-muted)" }}>
                Loading manifests, evaluation history, and integrity digests...
              </div>
            ) : (
              <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 20 }}>
                {/* Left Column: Lineage & Manifest */}
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  {/* Lineage Card */}
                  <div
                    style={{
                      backgroundColor: "var(--bg-app)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: 6,
                      padding: 16,
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-cyan)", marginBottom: 10 }}>
                      DATASET & FEATURE LINEAGE
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 12 }}>
                      <div>
                        <div style={{ color: "var(--text-muted)" }}>Dataset Identifier:</div>
                        <div style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)", fontWeight: 600 }}>
                          {selectedModel.dataset_identifier}
                        </div>
                      </div>
                      <div>
                        <div style={{ color: "var(--text-muted)" }}>Dataset Version / Split:</div>
                        <div style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>
                          {selectedModel.dataset_version || "Official Reference"}
                        </div>
                      </div>
                      <div>
                        <div style={{ color: "var(--text-muted)" }}>Feature Config Version:</div>
                        <div style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>
                          {selectedModel.feature_engineering_version}
                        </div>
                      </div>
                      <div>
                        <div style={{ color: "var(--text-muted)" }}>Artifact Path:</div>
                        <div style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)", fontSize: 11 }}>
                          {selectedModel.artifact_path}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Reproducibility Manifest */}
                  <div
                    style={{
                      backgroundColor: "var(--bg-app)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: 6,
                      padding: 16,
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-cyan)", marginBottom: 10 }}>
                      REPRODUCIBILITY MANIFEST
                    </div>
                    <pre
                      style={{
                        margin: 0,
                        backgroundColor: "rgba(0, 0, 0, 0.4)",
                        padding: 12,
                        borderRadius: 4,
                        fontSize: 11,
                        fontFamily: "var(--font-mono)",
                        color: "var(--text-secondary)",
                        overflowX: "auto",
                        maxHeight: 220,
                      }}
                    >
                      {JSON.stringify(selectedModel.training_manifest || selectedModel.hyperparameters, null, 2)}
                    </pre>
                  </div>

                  {/* Immutable Evaluation Records */}
                  <div
                    style={{
                      backgroundColor: "var(--bg-app)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: 6,
                      padding: 16,
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-cyan)", marginBottom: 10 }}>
                      IMMUTABLE EVALUATION RECORDS ({evaluations.length})
                    </div>
                    {evaluations.length === 0 ? (
                      <div style={{ fontSize: 12, color: "var(--text-muted)" }}>No evaluation records logged.</div>
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                        {evaluations.map((ev) => (
                          <div
                            key={ev.id}
                            style={{
                              backgroundColor: "rgba(255, 255, 255, 0.02)",
                              border: "1px solid var(--border-subtle)",
                              borderRadius: 4,
                              padding: 12,
                              fontSize: 12,
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                              <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{ev.evaluation_type}</span>
                              <span
                                style={{
                                  fontSize: 10,
                                  fontFamily: "var(--font-mono)",
                                  padding: "2px 6px",
                                  borderRadius: 3,
                                  backgroundColor: ev.gate_result === "PASSED" ? "rgba(0, 230, 118, 0.15)" : "rgba(255, 23, 68, 0.15)",
                                  color: ev.gate_result === "PASSED" ? "var(--risk-normal)" : "var(--risk-critical)",
                                }}
                              >
                                {ev.gate_result}
                              </span>
                            </div>
                            <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 6 }}>
                              Split: {ev.split} • Evaluator: {ev.evaluator} • {new Date(ev.evaluated_at).toLocaleDateString()}
                            </div>
                            <div
                              style={{
                                display: "grid",
                                gridTemplateColumns: "repeat(3, 1fr)",
                                gap: 6,
                                fontFamily: "var(--font-mono)",
                                fontSize: 11,
                                color: "var(--accent-cyan)",
                              }}
                            >
                              {Object.entries(ev.metrics).map(([k, v]) => (
                                <div key={k}>
                                  <span style={{ color: "var(--text-muted)" }}>{k}: </span>
                                  <span>{typeof v === "number" ? v.toFixed(4) : String(v)}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Right Column: Integrity, Gates & Audit Log */}
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  {/* Cryptographic Integrity Card */}
                  <div
                    style={{
                      backgroundColor: "var(--bg-app)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: 6,
                      padding: 16,
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-cyan)", marginBottom: 10 }}>
                      CRYPTOGRAPHIC SHA-256 INTEGRITY
                    </div>
                    {integrityReport ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 12 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <span style={{ color: "var(--text-muted)" }}>Status:</span>
                          <span
                            style={{
                              fontFamily: "var(--font-mono)",
                              fontWeight: 700,
                              color: integrityReport.is_valid ? "var(--risk-normal)" : "var(--risk-critical)",
                            }}
                          >
                            {integrityReport.is_valid ? "VALID & VERIFIED" : "COMPROMISED / MISMATCH"}
                          </span>
                        </div>
                        <div>
                          <div style={{ color: "var(--text-muted)", fontSize: 11 }}>Recorded Digest:</div>
                          <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-primary)", wordBreak: "break-all" }}>
                            {integrityReport.expected_sha256 || "None"}
                          </div>
                        </div>
                        <div>
                          <div style={{ color: "var(--text-muted)", fontSize: 11 }}>Computed File Hash:</div>
                          <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-primary)", wordBreak: "break-all" }}>
                            {integrityReport.computed_sha256 || "None"}
                          </div>
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                          Verified At: {new Date(integrityReport.verified_at).toLocaleTimeString()}
                        </div>
                      </div>
                    ) : (
                      <div style={{ fontSize: 12, color: "var(--text-muted)" }}>Checking integrity...</div>
                    )}
                  </div>

                  {/* Promotion Gates Evaluation Card */}
                  <div
                    style={{
                      backgroundColor: "var(--bg-app)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: 6,
                      padding: 16,
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-cyan)", marginBottom: 10 }}>
                      PROMOTION GATE READINESS
                    </div>
                    {gatesReport ? (
                      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
                          <span style={{ color: "var(--text-muted)" }}>Promotable:</span>
                          <span
                            style={{
                              fontFamily: "var(--font-mono)",
                              fontWeight: 700,
                              color: gatesReport.can_promote ? "var(--risk-normal)" : "var(--risk-critical)",
                            }}
                          >
                            {gatesReport.can_promote ? "READY FOR PROMOTION" : "GATES BLOCKED"}
                          </span>
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                          Policy: {gatesReport.policy_version}
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 4 }}>
                          {gatesReport.passed_gates.map((g) => (
                            <div key={g} style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--risk-normal)", display: "flex", alignItems: "center", gap: 6 }}>
                              <CheckCircle size={12} />
                              <span>{g}</span>
                            </div>
                          ))}
                          {gatesReport.failed_gates.map((g) => (
                            <div key={g} style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--risk-critical)", display: "flex", alignItems: "center", gap: 6 }}>
                              <AlertCircle size={12} />
                              <span>{g}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div style={{ fontSize: 12, color: "var(--text-muted)" }}>Evaluating gates...</div>
                    )}
                  </div>

                  {/* Operational Monitoring Summary */}
                  {monitoringSummary && (
                    <div
                      style={{
                        backgroundColor: "var(--bg-app)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: 6,
                        padding: 16,
                      }}
                    >
                      <div style={{ fontSize: 12, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-cyan)", marginBottom: 10 }}>
                        OPERATIONAL MONITORING ({monitoringSummary.data_classification})
                      </div>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 12 }}>
                        <div>
                          <div style={{ color: "var(--text-muted)" }}>Total Inferences:</div>
                          <div style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: "var(--text-primary)" }}>
                            {monitoringSummary.total_inferences}
                          </div>
                        </div>
                        <div>
                          <div style={{ color: "var(--text-muted)" }}>Last Inference:</div>
                          <div style={{ fontFamily: "var(--font-mono)", color: "var(--text-secondary)", fontSize: 11 }}>
                            {monitoringSummary.last_inference_timestamp
                              ? new Date(monitoringSummary.last_inference_timestamp).toLocaleDateString()
                              : "None recorded"}
                          </div>
                        </div>
                      </div>
                      <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 8, fontStyle: "italic" }}>
                        Metrics reflect empirical operational data. No synthetic drift baselines fabricated.
                      </div>
                    </div>
                  )}

                  {/* Promotion Audit Log */}
                  <div
                    style={{
                      backgroundColor: "var(--bg-app)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: 6,
                      padding: 16,
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-cyan)", marginBottom: 10 }}>
                      PROMOTION AUDIT TRAIL ({promotions.length})
                    </div>
                    {promotions.length === 0 ? (
                      <div style={{ fontSize: 12, color: "var(--text-muted)" }}>No promotion transitions recorded.</div>
                    ) : (
                      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        {promotions.map((p) => (
                          <div
                            key={p.id}
                            style={{
                              backgroundColor: "rgba(255, 255, 255, 0.02)",
                              border: "1px solid var(--border-subtle)",
                              borderRadius: 4,
                              padding: 10,
                              fontSize: 11,
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", color: "var(--accent-cyan)", fontFamily: "var(--font-mono)" }}>
                              <span>{p.from_status} → {p.to_status}</span>
                              <span style={{ color: "var(--text-muted)" }}>{new Date(p.promoted_at).toLocaleDateString()}</span>
                            </div>
                            <div style={{ marginTop: 4, color: "var(--text-secondary)" }}>
                              {p.reason}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Promotion / Retirement Action Modal */}
        {actionModal && selectedModel && (
          <div
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: "rgba(0, 0, 0, 0.75)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 1000,
            }}
          >
            <div
              style={{
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-md)",
                padding: 24,
                width: 480,
                display: "flex",
                flexDirection: "column",
                gap: 16,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>
                  {actionModal === "promote" ? "Promote Model to Production" : "Retire Model from Production"}
                </h3>
                <button
                  onClick={() => setActionModal(null)}
                  style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
                >
                  <X size={18} />
                </button>
              </div>

              <p style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                {actionModal === "promote"
                  ? `Promoting '${selectedModel.model_id}' will set it as the active production model for domain '${selectedModel.domain}', automatically retiring any currently active model.`
                  : `Retiring '${selectedModel.model_id}' will mark it as RETIRED and remove it from active serving.`}
              </p>

              <div>
                <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 6 }}>
                  Mandatory Audit Reason (min 5 chars):
                </label>
                <textarea
                  value={actionReason}
                  onChange={(e) => setActionReason(e.target.value)}
                  placeholder="e.g. Verified M4 evaluation RMSE meets production serving criteria."
                  rows={3}
                  style={{
                    width: "100%",
                    padding: 10,
                    backgroundColor: "var(--bg-app)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: 4,
                    color: "var(--text-primary)",
                    fontSize: 12,
                    fontFamily: "inherit",
                    resize: "vertical",
                  }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
                <button
                  onClick={() => setActionModal(null)}
                  style={{
                    padding: "8px 14px",
                    backgroundColor: "transparent",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: 4,
                    color: "var(--text-muted)",
                    fontSize: 12,
                    cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
                <button
                  disabled={actionReason.length < 5 || actionSubmitting}
                  onClick={handleExecutePromotion}
                  style={{
                    padding: "8px 16px",
                    backgroundColor: actionModal === "promote" ? "var(--accent-cyan)" : "var(--risk-critical)",
                    border: "none",
                    borderRadius: 4,
                    color: actionModal === "promote" ? "#000" : "#fff",
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: actionReason.length >= 5 && !actionSubmitting ? "pointer" : "not-allowed",
                    opacity: actionReason.length >= 5 && !actionSubmitting ? 1 : 0.5,
                  }}
                >
                  {actionSubmitting ? "Processing..." : actionModal === "promote" ? "Confirm Promotion" : "Confirm Retirement"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
