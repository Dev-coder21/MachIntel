"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { StatusBadge } from "@/components/common/StatusBadge";
import { EmptyState } from "@/components/common/EmptyState";
import { apiClient, ApiClientError } from "@/lib/api-client";
import { MachineDetail } from "@/types/machine";
import { PredictionItem } from "@/types/prediction";
import { RiskAssessmentItem } from "@/types/risk";
import { AlertItem } from "@/types/alert";
import { EvidenceChain } from "@/components/evidence/EvidenceChain";
import {
  CorrelationMatrixResponse,
  FeaturePreviewResponse,
  MachineAnalyticsSummary,
  MachineComparisonResponse,
  SensorSummaryItem,
  SensorTrendResponse,
} from "@/types/analytics";
import { MaintenanceWorkOrder } from "@/types/maintenance";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  BarChart3,
  Bot,
  CheckCircle,
  Clock,
  Cpu,
  Database,
  Flame,
  Gauge,
  Grid,
  Info,
  Layers,
  LineChart,
  RefreshCw,
  Sliders,
  Sparkles,
  Table as TableIcon,
  TrendingDown,
  TrendingUp,
  Wind,
  Wrench,
  Zap,
} from "lucide-react";

const SENSOR_CHANNELS = [
  { key: "sensor_2", label: "Sensor 2 (T24)", desc: "Total Temperature at LPC Outlet", unit: "°R" },
  { key: "sensor_3", label: "Sensor 3 (T30)", desc: "Total Temperature at HPC Outlet", unit: "°R" },
  { key: "sensor_4", label: "Sensor 4 (T50)", desc: "Total Temperature at LPT Outlet", unit: "°R" },
  { key: "sensor_6", label: "Sensor 6 (P2)", desc: "Total Pressure in Bypass Duct", unit: "psia" },
  { key: "sensor_7", label: "Sensor 7 (P30)", desc: "Total Pressure at HPC Outlet", unit: "psia" },
  { key: "sensor_8", label: "Sensor 8 (Nf)", desc: "Physical Fan Speed", unit: "rpm" },
  { key: "sensor_9", label: "Sensor 9 (Nc)", desc: "Physical Core Speed", unit: "rpm" },
  { key: "sensor_11", label: "Sensor 11 (Ps30)", desc: "Static Pressure at HPC Outlet", unit: "psia" },
  { key: "sensor_12", label: "Sensor 12 (phi)", desc: "Ratio of Fuel Flow to Ps30", unit: "pps/psi" },
  { key: "sensor_13", label: "Sensor 13 (NRf)", desc: "Corrected Fan Speed", unit: "rpm" },
  { key: "sensor_14", label: "Sensor 14 (NRc)", desc: "Corrected Core Speed", unit: "rpm" },
  { key: "sensor_15", label: "Sensor 15 (BPR)", desc: "Bypass Ratio", unit: "—" },
  { key: "sensor_17", label: "Sensor 17 (htBleed)", desc: "Bleed Enthalpy", unit: "—" },
  { key: "sensor_20", label: "Sensor 20 (W31)", desc: "HPT Coolant Bleed", unit: "lbm/s" },
  { key: "sensor_21", label: "Sensor 21 (W32)", desc: "LPT Coolant Bleed", unit: "lbm/s" },
  { key: "op_setting_1", label: "Op Setting 1", desc: "Mach Number / Flight Condition", unit: "Mach" },
  { key: "op_setting_2", label: "Op Setting 2", desc: "Throttle Resolver Angle", unit: "TRA" },
];

export default function MachineDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = React.use(params);

  const [machine, setMachine] = useState<MachineDetail | null>(null);
  const [summary, setSummary] = useState<MachineAnalyticsSummary | null>(null);
  const [trends, setTrends] = useState<SensorTrendResponse | null>(null);
  const [correlation, setCorrelation] = useState<CorrelationMatrixResponse | null>(null);
  const [features, setFeatures] = useState<FeaturePreviewResponse | null>(null);
  const [comparison, setComparison] = useState<MachineComparisonResponse | null>(null);

  const [activeTab, setActiveTab] = useState<"stream" | "prognostics" | "evidence" | "maintenance" | "stats" | "correlation" | "features" | "compare">("stream");
  const [evidenceTimeline, setEvidenceTimeline] = useState<any[]>([]);
  const [isLoadingEvidence, setIsLoadingEvidence] = useState<boolean>(false);
  const [maintenanceOrders, setMaintenanceOrders] = useState<MaintenanceWorkOrder[]>([]);
  const [isLoadingMaintenance, setIsLoadingMaintenance] = useState<boolean>(false);
  const [isDraftingRecommendation, setIsDraftingRecommendation] = useState<boolean>(false);
  const [draftMsg, setDraftMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [selectedSensor, setSelectedSensor] = useState<string>("sensor_2");
  const [windowSize, setWindowSize] = useState<number>(20);
  const [chartMode, setChartMode] = useState<"overlay" | "rolling_only" | "raw_only">("overlay");
  const [compareTargetId, setCompareTargetId] = useState<string>("TURBOFAN-ENG-002");

  // Prognostics & ML state
  const [latestPrediction, setLatestPrediction] = useState<PredictionItem | null>(null);
  const [predictionHistory, setPredictionHistory] = useState<PredictionItem[]>([]);
  const [latestRisk, setLatestRisk] = useState<RiskAssessmentItem | null>(null);
  const [riskHistory, setRiskHistory] = useState<RiskAssessmentItem[]>([]);
  const [activeAlert, setActiveAlert] = useState<AlertItem | null>(null);
  const [targetCycle, setTargetCycle] = useState<number>(1);
  const [isPredicting, setIsPredicting] = useState<boolean>(false);
  const [predictFeedback, setPredictFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isLoadingTrends, setIsLoadingTrends] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load primary machine data, summary, initial trends, prognostics, risk, and alerts
  useEffect(() => {
    let isMounted = true;

    async function loadInitial() {
      setIsLoading(true);
      setError(null);
      try {
        const [m, sum, tr, corr, feat, latestPred, predHistory, riskLatest, riskHist, alertsRes] = await Promise.all([
          apiClient.getMachine(id),
          apiClient.getMachineAnalyticsSummary(id),
          apiClient.getMachineSensorTrends(id, selectedSensor, { window: windowSize }),
          apiClient.getMachineCorrelation(id),
          apiClient.getMachineFeaturePreview(id, { start_cycle: 1, end_cycle: 20, window: windowSize }),
          apiClient.getMachineLatestPrediction(id).catch(() => null),
          apiClient.getMachinePredictionHistory(id, 1, 50).catch(() => ({ total: 0, page: 1, page_size: 50, items: [] })),
          apiClient.getMachineLatestRisk(id).catch(() => null),
          apiClient.getMachineRiskHistory(id, 0, 50).catch(() => []),
          apiClient.getAlerts({ machine_id: id, limit: 5 }).catch(() => ({ alerts: [], total: 0, skip: 0, limit: 5 })),
        ]);

        if (!isMounted) return;
        setMachine(m);
        setSummary(sum);
        setTrends(tr);
        setCorrelation(corr);
        setFeatures(feat);
        setLatestPrediction(latestPred);
        setPredictionHistory(predHistory.items);
        setLatestRisk(riskLatest);
        setRiskHistory(riskHist);
        const openOrAck = alertsRes.alerts.find((a) => a.status === "OPEN" || a.status === "ACKNOWLEDGED");
        setActiveAlert(openOrAck || alertsRes.alerts[0] || null);

        if (m.max_cycle) {
          setTargetCycle(m.max_cycle);
        }
      } catch (err) {
        if (!isMounted) return;
        if (err instanceof ApiClientError) {
          setError(err.message);
        } else {
          setError("Failed to retrieve machine analytics.");
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    loadInitial();
    return () => {
      isMounted = false;
    };
  }, [id]);

  const handleRunInference = async (cycleToUse?: number) => {
    if (!machine) return;
    const cycle = cycleToUse ?? targetCycle;
    setIsPredicting(true);
    setPredictFeedback(null);
    try {
      const pred = await apiClient.createMachinePrediction(machine.machine_id, {
        observation_cycle: cycle,
      });
      setLatestPrediction(pred);
      const [hist, riskLatest, riskHist, alertsRes] = await Promise.all([
        apiClient.getMachinePredictionHistory(machine.machine_id, 1, 50),
        apiClient.getMachineLatestRisk(machine.machine_id).catch(() => null),
        apiClient.getMachineRiskHistory(machine.machine_id, 0, 50).catch(() => []),
        apiClient.getAlerts({ machine_id: machine.machine_id, limit: 5 }).catch(() => ({ alerts: [], total: 0, skip: 0, limit: 5 })),
      ]);
      setPredictionHistory(hist.items);
      setLatestRisk(riskLatest);
      setRiskHistory(riskHist);
      const openOrAck = alertsRes.alerts.find((a) => a.status === "OPEN" || a.status === "ACKNOWLEDGED");
      setActiveAlert(openOrAck || alertsRes.alerts[0] || null);

      setPredictFeedback({
        type: "success",
        message: `Inference & Risk Evaluation completed for Cycle ${cycle}: Estimated RUL = ${pred.predicted_rul.toFixed(1)} cyc, State = ${pred.operational_state}`,
      });
    } catch (err: any) {
      setPredictFeedback({
        type: "error",
        message: err?.message || "Failed to execute prognostic inference.",
      });
    } finally {
      setIsPredicting(false);
    }
  };

  // Handle sensor channel or window change for trends chart
  useEffect(() => {
    let isMounted = true;
    async function updateTrends() {
      setIsLoadingTrends(true);
      try {
        const tr = await apiClient.getMachineSensorTrends(id, selectedSensor, { window: windowSize });
        if (!isMounted) return;
        setTrends(tr);
      } catch {
        // Handled silently
      } finally {
        if (isMounted) setIsLoadingTrends(false);
      }
    }

    if (!isLoading) {
      updateTrends();
    }

    return () => {
      isMounted = false;
    };
  }, [id, selectedSensor, windowSize]);

  // Load machine evidence timeline when evidence tab is activated
  useEffect(() => {
    let isMounted = true;
    async function loadEvidence() {
      if (activeTab === "evidence") {
        setIsLoadingEvidence(true);
        try {
          const ev = await apiClient.getEntityEvidenceTimeline("MACHINE", id);
          if (!isMounted) return;
          setEvidenceTimeline(ev);
        } catch {
          // Handled silently
        } finally {
          if (isMounted) setIsLoadingEvidence(false);
        }
      }
    }
    loadEvidence();
    return () => {
      isMounted = false;
    };
  }, [id, activeTab]);

  // Load maintenance work orders when maintenance tab is activated
  useEffect(() => {
    let isMounted = true;
    async function loadMaintenance() {
      if (activeTab === "maintenance" && machine) {
        setIsLoadingMaintenance(true);
        try {
          const wos = await apiClient.listWorkOrders({
            machine_id: machine.machine_id,
            limit: 50,
          });
          if (!isMounted) return;
          setMaintenanceOrders(wos);
        } catch {
          // Handled silently
        } finally {
          if (isMounted) setIsLoadingMaintenance(false);
        }
      }
    }
    loadMaintenance();
    return () => {
      isMounted = false;
    };
  }, [machine, activeTab]);

  const handleDraftMaintenanceFromRisk = async () => {
    if (!latestRisk) return;
    try {
      setIsDraftingRecommendation(true);
      setDraftMsg(null);
      await apiClient.draftRecommendationFromRisk(latestRisk.id);
      setDraftMsg({ type: "success", text: "Maintenance recommendation drafted successfully!" });
      if (machine) {
        const wos = await apiClient.listWorkOrders({ machine_id: machine.machine_id, limit: 50 });
        setMaintenanceOrders(wos);
      }
    } catch (err: any) {
      setDraftMsg({ type: "error", text: err?.message || "Failed to draft recommendation." });
    } finally {
      setIsDraftingRecommendation(false);
    }
  };

  // Load comparison when tab is activated
  useEffect(() => {
    let isMounted = true;
    async function loadComparison() {
      if (activeTab === "compare") {
        try {
          const comp = await apiClient.compareMachines([id, compareTargetId]);
          if (!isMounted) return;
          setComparison(comp);
        } catch {
          // Handled silently
        }
      }
    }

    loadComparison();
    return () => {
      isMounted = false;
    };
  }, [id, compareTargetId, activeTab]);

  const activeChannelMeta = SENSOR_CHANNELS.find((c) => c.key === selectedSensor) || {
    label: selectedSensor,
    desc: "Active Sensor",
    unit: "",
  };

  return (
    <AppShell>
      {/* Back Link */}
      <div style={{ marginBottom: 16 }}>
        <Link
          href="/machines"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            color: "var(--text-muted)",
            fontSize: 12,
            fontFamily: "var(--font-mono)",
            textDecoration: "none",
          }}
        >
          <ArrowLeft size={13} />
          BACK TO MACHINE REGISTRY
        </Link>
      </div>

      <PageHeader
        title={`Asset Analytics: ${machine?.machine_id || id}`}
        subtitle="Forensic telemetry investigation, temporal rolling statistics, and causal feature extraction workspace."
        breadcrumbs={[
          { label: "Operations", href: "/" },
          { label: "Machine Registry", href: "/machines" },
          { label: machine?.machine_id || id },
        ]}
        badge={
          machine ? (
            <StatusBadge
              status={
                machine.status === "OPERATIONAL"
                  ? "ACTIVE"
                  : machine.status === "DEGRADED"
                  ? "WATCH"
                  : "CRITICAL"
              }
              label={machine.status}
            />
          ) : undefined
        }
        actions={
          machine ? (
            <Link
              href={`/ai-inspector?machine_id=${encodeURIComponent(machine.machine_id)}&question=${encodeURIComponent(`What is the current health state and evidence for ${machine.machine_id}?`)}`}
              className="btn btn-secondary"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                textDecoration: "none",
                padding: "6px 12px",
              }}
            >
              <Bot size={14} style={{ color: "var(--accent-cyan)" }} />
              INVESTIGATE WITH AI INSPECTOR
            </Link>
          ) : undefined
        }
      />

      {/* Error state */}
      {error && (
        <div
          style={{
            padding: "16px 20px",
            backgroundColor: "rgba(239, 68, 68, 0.1)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: "var(--radius-sm)",
            color: "var(--risk-critical)",
            fontSize: 13,
            marginBottom: 24,
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}
        >
          <AlertCircle size={18} />
          <div>{error}</div>
        </div>
      )}

      {/* Machine Overview Metadata Cards */}
      {machine && summary && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
            gap: 14,
            marginBottom: 24,
          }}
        >
          <div className="tech-card">
            <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 6 }}>
              ASSET PROFILE
            </div>
            <div style={{ fontSize: 15, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>
              {machine.machine_id}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>
              Unit #{machine.source_entity_id} • {machine.split_category}
            </div>
          </div>

          <div className="tech-card">
            <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 6 }}>
              OPERATING LIFESPAN
            </div>
            <div style={{ fontSize: 15, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-cyan)" }}>
              {summary.total_cycles} Cycles Recorded
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
              Span: Cycle {summary.first_cycle} → {summary.latest_cycle}
            </div>
          </div>

          <div className="tech-card">
            <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 6 }}>
              FEATURE ENGINEERING
            </div>
            <div style={{ fontSize: 15, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>
              15 Active / 7 Invariant
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
              Temporal Window W={windowSize} Causal
            </div>
          </div>

          <div className="tech-card">
            <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 6 }}>
              TOP SENSOR DRIFT
            </div>
            <div style={{ fontSize: 13, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--risk-critical)" }}>
              {summary.top_drifting_sensors[0]?.channel_name.split("(")[0] || "—"}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
              {summary.top_drifting_sensors[0]?.pct_change !== null
                ? `${summary.top_drifting_sensors[0]?.pct_change}% (${summary.top_drifting_sensors[0]?.direction})`
                : "Calculated"}
            </div>
          </div>
        </div>
      )}

      {/* Asset Lifecycle Story Pipeline Banner */}
      {machine && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "10px 16px",
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-sm)",
            marginBottom: 16,
            overflowX: "auto",
            fontSize: 11,
            fontFamily: "var(--font-mono)",
            whiteSpace: "nowrap",
          }}
        >
          <span style={{ color: "var(--text-muted)", fontWeight: 600 }}>ASSET STORY:</span>
          <button type="button" onClick={() => setActiveTab("stream")} style={{ color: activeTab === "stream" ? "var(--accent-cyan)" : "var(--text-secondary)", fontWeight: 500, cursor: "pointer" }}>TELEMETRY</button>
          <span style={{ color: "var(--border-default)" }}>→</span>
          <button type="button" onClick={() => setActiveTab("prognostics")} style={{ color: activeTab === "prognostics" ? "var(--accent-cyan)" : "var(--text-secondary)", fontWeight: 500, cursor: "pointer" }}>HEALTH INDEX</button>
          <span style={{ color: "var(--border-default)" }}>→</span>
          <button type="button" onClick={() => setActiveTab("prognostics")} style={{ color: activeTab === "prognostics" ? "var(--accent-cyan)" : "var(--text-secondary)", fontWeight: 500, cursor: "pointer" }}>ESTIMATED RUL</button>
          <span style={{ color: "var(--border-default)" }}>→</span>
          <button type="button" onClick={() => setActiveTab("prognostics")} style={{ color: activeTab === "prognostics" ? "var(--accent-cyan)" : "var(--text-secondary)", fontWeight: 500, cursor: "pointer" }}>RISK STATE</button>
          <span style={{ color: "var(--border-default)" }}>→</span>
          <button type="button" onClick={() => setActiveTab("evidence")} style={{ color: activeTab === "evidence" ? "var(--accent-cyan)" : "var(--text-secondary)", fontWeight: 500, cursor: "pointer" }}>EVIDENCE LINEAGE</button>
          <span style={{ color: "var(--border-default)" }}>→</span>
          <Link href="/alerts" style={{ color: "var(--text-secondary)", fontWeight: 500 }}>ACTIVE ALERTS</Link>
          <span style={{ color: "var(--border-default)" }}>→</span>
          <button type="button" onClick={() => setActiveTab("maintenance")} style={{ color: activeTab === "maintenance" ? "var(--accent-cyan)" : "var(--text-secondary)", fontWeight: 500, cursor: "pointer" }}>MAINTENANCE ORDER</button>
        </div>
      )}

      {/* Main Analytical Investigation Workspace */}
      <div
        style={{
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-sm)",
          overflow: "hidden",
          marginBottom: 24,
        }}
      >
        {/* Navigation Tabs */}
        <div
          style={{
            display: "flex",
            borderBottom: "1px solid var(--border-default)",
            backgroundColor: "rgba(0, 0, 0, 0.2)",
            overflowX: "auto",
          }}
        >
          {[
            { id: "stream", label: "TELEMETRY & ROLLING TRENDS", icon: <LineChart size={14} /> },
            { id: "prognostics", label: "PROGNOSTICS & RUL", icon: <Gauge size={14} /> },
            { id: "evidence", label: "EVIDENCE LINEAGE", icon: <Activity size={14} /> },
            { id: "maintenance", label: "MAINTENANCE ORDERS", icon: <Wrench size={14} /> },
            { id: "stats", label: "SENSOR STATISTICS MATRIX", icon: <BarChart3 size={14} /> },
            { id: "correlation", label: "SENSOR CORRELATION", icon: <Grid size={14} /> },
            { id: "features", label: "ML FEATURE PREVIEW", icon: <Cpu size={14} /> },
            { id: "compare", label: "ASSET COMPARISON", icon: <Sliders size={14} /> },
          ].map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "12px 18px",
                  fontSize: 12,
                  fontFamily: "var(--font-mono)",
                  fontWeight: isActive ? 600 : 400,
                  color: isActive ? "var(--accent-cyan)" : "var(--text-secondary)",
                  backgroundColor: isActive ? "rgba(0, 229, 255, 0.08)" : "transparent",
                  border: "none",
                  borderBottom: isActive ? "2px solid var(--accent-cyan)" : "2px solid transparent",
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                  transition: "all 0.15s ease",
                }}
              >
                {tab.icon}
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Tab 1: Telemetry & Rolling Trends */}
        {activeTab === "stream" && (
          <div style={{ padding: 20 }}>
            {/* Controls Bar */}
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                justifyContent: "space-between",
                alignItems: "center",
                gap: 16,
                marginBottom: 20,
                paddingBottom: 16,
                borderBottom: "1px solid var(--border-subtle)",
              }}
            >
              {/* Channel Selector */}
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                  ACTIVE CHANNEL:
                </span>
                <select
                  value={selectedSensor}
                  onChange={(e) => setSelectedSensor(e.target.value)}
                  style={{
                    padding: "7px 12px",
                    backgroundColor: "var(--bg-app)",
                    border: "1px solid var(--border-default)",
                    borderRadius: "var(--radius-sm)",
                    color: "var(--text-primary)",
                    fontSize: 12,
                    fontFamily: "var(--font-mono)",
                    outline: "none",
                    cursor: "pointer",
                  }}
                >
                  {SENSOR_CHANNELS.map((ch) => (
                    <option key={ch.key} value={ch.key}>
                      {ch.label} — {ch.desc}
                    </option>
                  ))}
                </select>
              </div>

              {/* View Overlay Mode & Window Selector */}
              <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                    WINDOW W:
                  </span>
                  <select
                    value={windowSize}
                    onChange={(e) => setWindowSize(Number(e.target.value))}
                    style={{
                      padding: "5px 10px",
                      backgroundColor: "var(--bg-app)",
                      border: "1px solid var(--border-default)",
                      borderRadius: "var(--radius-xs)",
                      color: "var(--accent-cyan)",
                      fontSize: 11,
                      fontFamily: "var(--font-mono)",
                      outline: "none",
                    }}
                  >
                    <option value={10}>10 Cycles</option>
                    <option value={20}>20 Cycles (M4 Standard)</option>
                    <option value={30}>30 Cycles</option>
                  </select>
                </div>

                <div
                  style={{
                    display: "flex",
                    backgroundColor: "var(--bg-app)",
                    border: "1px solid var(--border-default)",
                    borderRadius: "var(--radius-xs)",
                    padding: 2,
                  }}
                >
                  {[
                    { id: "overlay", label: "DUAL OVERLAY" },
                    { id: "rolling_only", label: "ROLLING MEAN (W=20)" },
                    { id: "raw_only", label: "RAW SENSOR" },
                  ].map((mode) => (
                    <button
                      key={mode.id}
                      onClick={() => setChartMode(mode.id as any)}
                      style={{
                        padding: "5px 10px",
                        fontSize: 11,
                        fontFamily: "var(--font-mono)",
                        fontWeight: chartMode === mode.id ? 600 : 400,
                        backgroundColor: chartMode === mode.id ? "rgba(0, 229, 255, 0.12)" : "transparent",
                        color: chartMode === mode.id ? "var(--accent-cyan)" : "var(--text-secondary)",
                        border: "none",
                        borderRadius: "var(--radius-xs)",
                        cursor: "pointer",
                      }}
                    >
                      {mode.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Trends Chart & Metrics */}
            {isLoadingTrends ? (
              <div style={{ padding: 60, textAlign: "center", color: "var(--accent-cyan)", fontFamily: "var(--font-mono)", fontSize: 12 }}>
                <RefreshCw size={18} className="spin" style={{ display: "inline-block", marginBottom: 8 }} />
                <div>COMPUTING CAUSAL ROLLING WINDOW STATISTICS...</div>
              </div>
            ) : trends && trends.points.length > 0 ? (
              <div>
                {/* Channel Stats Overview */}
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
                    gap: 12,
                    backgroundColor: "rgba(0, 0, 0, 0.2)",
                    padding: "12px 16px",
                    borderRadius: "var(--radius-xs)",
                    border: "1px solid var(--border-subtle)",
                    marginBottom: 20,
                  }}
                >
                  <div>
                    <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>CHANNEL</div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "var(--accent-cyan)", fontFamily: "var(--font-mono)" }}>
                      {activeChannelMeta.label}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>DIRECTION</div>
                    <div
                      style={{
                        fontSize: 13,
                        fontWeight: 700,
                        fontFamily: "var(--font-mono)",
                        color: trends.direction === "INCREASING" ? "var(--risk-critical)" : "var(--accent-cyan)",
                      }}
                    >
                      {trends.direction}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>ROLLING SLOPE (OLS)</div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                      {trends.overall_slope > 0 ? `+${trends.overall_slope}` : trends.overall_slope}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>FINAL ROLLING MEAN</div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                      {trends.points[trends.points.length - 1].rolling_mean.toFixed(3)} {activeChannelMeta.unit}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>FINAL ROLLING STD (σ)</div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>
                      ±{trends.points[trends.points.length - 1].rolling_std.toFixed(3)}
                    </div>
                  </div>
                </div>

                {/* SVG Chart */}
                <div style={{ width: "100%", height: 320, position: "relative" }}>
                  {(() => {
                    const width = 800;
                    const height = 280;
                    const padding = { top: 20, right: 30, bottom: 40, left: 65 };

                    const pts = trends.points;
                    const allVals = pts.flatMap((p) => [p.raw_value, p.rolling_mean, p.rolling_mean + p.rolling_std, p.rolling_mean - p.rolling_std]);
                    const minVal = Math.min(...allVals);
                    const maxVal = Math.max(...allVals);
                    const rangeVal = maxVal - minVal === 0 ? 1 : maxVal - minVal;

                    const minCycle = pts[0].cycle;
                    const maxCycle = pts[pts.length - 1].cycle;
                    const rangeCycle = maxCycle - minCycle === 0 ? 1 : maxCycle - minCycle;

                    const getX = (c: number) => padding.left + ((c - minCycle) / rangeCycle) * (width - padding.left - padding.right);
                    const getY = (v: number) => height - padding.bottom - ((v - minVal) / rangeVal) * (height - padding.top - padding.bottom);

                    const rawPathD = pts.map((p, idx) => `${idx === 0 ? "M" : "L"} ${getX(p.cycle).toFixed(1)} ${getY(p.raw_value).toFixed(1)}`).join(" ");
                    const rollingPathD = pts.map((p, idx) => `${idx === 0 ? "M" : "L"} ${getX(p.cycle).toFixed(1)} ${getY(p.rolling_mean).toFixed(1)}`).join(" ");

                    // Std dev envelope
                    const upperPts = pts.map((p) => `${getX(p.cycle).toFixed(1)} ${getY(p.rolling_mean + p.rolling_std).toFixed(1)}`);
                    const lowerPts = pts.slice().reverse().map((p) => `${getX(p.cycle).toFixed(1)} ${getY(p.rolling_mean - p.rolling_std).toFixed(1)}`);
                    const envelopeD = `M ${upperPts.join(" L ")} L ${lowerPts.join(" L ")} Z`;

                    return (
                      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height: "100%", overflow: "visible" }}>
                        <defs>
                          <linearGradient id="envelopeGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="var(--accent-cyan)" stopOpacity="0.18" />
                            <stop offset="100%" stopColor="var(--accent-cyan)" stopOpacity="0.04" />
                          </linearGradient>
                        </defs>

                        {/* Horizontal Grid lines */}
                        {[0, 0.25, 0.5, 0.75, 1].map((pct, idx) => {
                          const y = height - padding.bottom - pct * (height - padding.top - padding.bottom);
                          const val = minVal + pct * rangeVal;
                          return (
                            <g key={idx}>
                              <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="var(--border-subtle)" strokeDasharray="4 4" />
                              <text x={padding.left - 10} y={y + 4} textAnchor="end" fill="var(--text-muted)" fontSize="10" fontFamily="var(--font-mono)">
                                {val.toFixed(2)}
                              </text>
                            </g>
                          );
                        })}

                        {/* Vertical Cycle Ticks */}
                        {[0, 0.25, 0.5, 0.75, 1].map((pct, idx) => {
                          const c = Math.round(minCycle + pct * rangeCycle);
                          const x = getX(c);
                          return (
                            <g key={idx}>
                              <line x1={x} y1={padding.top} x2={x} y2={height - padding.bottom} stroke="var(--border-subtle)" strokeDasharray="4 4" />
                              <text x={x} y={height - padding.bottom + 18} textAnchor="middle" fill="var(--text-muted)" fontSize="10" fontFamily="var(--font-mono)">
                                Cycle {c}
                              </text>
                            </g>
                          );
                        })}

                        {/* Std Dev Envelope Area */}
                        {(chartMode === "overlay" || chartMode === "rolling_only") && (
                          <path d={envelopeD} fill="url(#envelopeGrad)" />
                        )}

                        {/* Raw Line */}
                        {(chartMode === "overlay" || chartMode === "raw_only") && (
                          <path d={rawPathD} fill="none" stroke="rgba(255, 255, 255, 0.35)" strokeWidth="1" strokeDasharray="2 2" />
                        )}

                        {/* Rolling Mean Line */}
                        {(chartMode === "overlay" || chartMode === "rolling_only") && (
                          <path d={rollingPathD} fill="none" stroke="var(--accent-cyan)" strokeWidth="2.5" strokeLinecap="round" />
                        )}
                      </svg>
                    );
                  })()}
                </div>

                {/* Legend & Causality Tag */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "8px 12px",
                    borderTop: "1px solid var(--border-subtle)",
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                    color: "var(--text-muted)",
                    flexWrap: "wrap",
                    gap: 8,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <span style={{ width: 14, height: 2, backgroundColor: "rgba(255, 255, 255, 0.4)", borderStyle: "dashed" }} />
                      <span>Raw Sensor Values</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <span style={{ width: 14, height: 3, backgroundColor: "var(--accent-cyan)" }} />
                      <span>Rolling Mean (W={windowSize})</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <span style={{ width: 14, height: 8, backgroundColor: "rgba(0, 229, 255, 0.2)" }} />
                      <span>Rolling Std Envelope (±1σ)</span>
                    </div>
                  </div>
                  <span>TEMPORALLY CAUSAL (NO FUTURE LOOKAHEAD)</span>
                </div>
              </div>
            ) : (
              <EmptyState icon="database" metadataTag="NO DATA" title="No Trends Available" description="No telemetry records match." />
            )}
          </div>
        )}

        {/* Tab: Prognostics & Remaining Useful Life */}
        {activeTab === "prognostics" && (
          <div style={{ padding: 20 }}>
            {/* Active Operational Alert Banner (if alert exists) */}
            {activeAlert && (activeAlert.status === "OPEN" || activeAlert.status === "ACKNOWLEDGED") && (
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "14px 18px",
                  borderRadius: 8,
                  backgroundColor:
                    activeAlert.severity === "CRITICAL"
                      ? "rgba(239, 68, 68, 0.12)"
                      : activeAlert.severity === "WARNING"
                      ? "rgba(245, 158, 11, 0.12)"
                      : "rgba(6, 182, 212, 0.12)",
                  border: `1px solid ${
                    activeAlert.severity === "CRITICAL"
                      ? "rgba(239, 68, 68, 0.4)"
                      : activeAlert.severity === "WARNING"
                      ? "rgba(245, 158, 11, 0.4)"
                      : "rgba(6, 182, 212, 0.4)"
                  }`,
                  marginBottom: 20,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <AlertTriangle
                    size={20}
                    color={
                      activeAlert.severity === "CRITICAL"
                        ? "var(--risk-critical)"
                        : activeAlert.severity === "WARNING"
                        ? "var(--risk-elevated)"
                        : "var(--risk-watch)"
                    }
                  />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
                      ACTIVE OPERATIONAL ALERT: {activeAlert.title}
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
                      {activeAlert.description} • Status: <strong>{activeAlert.status}</strong>
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <StatusBadge status={activeAlert.severity} />
                  <Link
                    href="/alerts"
                    style={{
                      fontSize: 11,
                      fontFamily: "var(--font-mono)",
                      color: "var(--accent-cyan)",
                      textDecoration: "none",
                      padding: "4px 10px",
                      borderRadius: 4,
                      backgroundColor: "rgba(0, 229, 255, 0.1)",
                      border: "1px solid rgba(0, 229, 255, 0.3)",
                    }}
                  >
                    VIEW IN ALERT CONSOLE →
                  </Link>
                </div>
              </div>
            )}

            {/* Analytical Risk Disclaimer Banner */}
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 12,
                padding: "12px 16px",
                borderRadius: 8,
                backgroundColor: "rgba(0, 229, 255, 0.04)",
                border: "1px solid rgba(0, 229, 255, 0.2)",
                marginBottom: 20,
              }}
            >
              <Info size={16} color="var(--accent-cyan)" style={{ marginTop: 2, flexShrink: 0 }} />
              <div style={{ fontSize: 12, lineHeight: 1.5, color: "var(--text-secondary)" }}>
                <strong style={{ color: "var(--text-primary)" }}>Analytical Risk Formulation: </strong>
                Estimated Remaining Useful Life is derived from causal regression features (W=20) on NASA C-MAPSS FD001. Operational state is a deterministic risk interpretation (<code style={{ fontFamily: "var(--font-mono)", color: "var(--accent-cyan)" }}>HI = clamp(RUL / 125, 0, 1)</code>). Not a guaranteed failure prediction.
              </div>
            </div>

            {/* Current Prediction Hero Card */}
            {latestPrediction ? (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: 16,
                  marginBottom: 24,
                  backgroundColor: "rgba(0, 0, 0, 0.2)",
                  padding: 16,
                  borderRadius: 8,
                  border: "1px solid var(--border-default)",
                }}
              >
                <div>
                  <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 4 }}>
                    ESTIMATED REMAINING USEFUL LIFE
                  </div>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 8 }}>
                    <span style={{ fontSize: 32, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>
                      {latestPrediction.predicted_rul.toFixed(1)}
                    </span>
                    <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>cycles remaining</span>
                  </div>
                  {/* Progress bar relative to RUL_max = 125 */}
                  <div style={{ width: "100%", height: 6, borderRadius: 3, backgroundColor: "var(--bg-secondary)", overflow: "hidden" }}>
                    <div
                      style={{
                        width: `${Math.min(100, (latestPrediction.predicted_rul / 125) * 100)}%`,
                        height: "100%",
                        backgroundColor:
                          latestPrediction.operational_state === "NORMAL"
                            ? "#10B981"
                            : latestPrediction.operational_state === "WATCH"
                            ? "#06B6D4"
                            : latestPrediction.operational_state === "ELEVATED"
                            ? "#F59E0B"
                            : "#EF4444",
                      }}
                    />
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 4 }}>
                    NORMALIZED HEALTH INDEX
                  </div>
                  <div style={{ fontSize: 32, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-cyan)", marginBottom: 4 }}>
                    {latestPrediction.health_index.toFixed(3)}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                    Scale: 0.0 (Degraded) to 1.0 (Nominal)
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 4 }}>
                    ANALYTICAL HEALTH STATE
                  </div>
                  <div style={{ marginTop: 6, marginBottom: 8 }}>
                    <StatusBadge status={latestPrediction.operational_state} />
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                    {latestPrediction.operational_state === "NORMAL" && "Operating within nominal parameter margins"}
                    {latestPrediction.operational_state === "WATCH" && "Incipient degradation drift observed"}
                    {latestPrediction.operational_state === "ELEVATED" && "Moderate high-pressure compressor degradation"}
                    {latestPrediction.operational_state === "CRITICAL" && "Approaching end of operational life threshold"}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 4 }}>
                    INFERENCE PROVENANCE
                  </div>
                  <div style={{ fontSize: 12, fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
                    Observed: Cycle {latestPrediction.observation_cycle}
                  </div>
                  <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginTop: 2 }}>
                    Model: {latestPrediction.model_version}
                  </div>
                  <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginTop: 2 }}>
                    Features: v{latestPrediction.feature_version} (W=20)
                  </div>
                </div>
              </div>
            ) : (
              <div
                style={{
                  padding: 24,
                  textAlign: "center",
                  borderRadius: 8,
                  backgroundColor: "rgba(0, 0, 0, 0.2)",
                  border: "1px dashed var(--border-default)",
                  marginBottom: 20,
                  color: "var(--text-muted)",
                }}
              >
                No predictions recorded yet for this engine. Use the live inference trigger below to generate an empirical RUL estimate.
              </div>
            )}

            {/* Deterministic Risk Intelligence Evidence Chain */}
            {latestRisk && (
              <div style={{ marginBottom: 24 }}>
                <EvidenceChain assessment={latestRisk} />
              </div>
            )}

            {/* Live Interactive Inference Trigger Card */}
            <div
              style={{
                padding: "16px 20px",
                borderRadius: 8,
                backgroundColor: "var(--bg-secondary)",
                border: "1px solid var(--border-default)",
                marginBottom: 24,
              }}
            >
              <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: 16 }}>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>
                    Trigger Real Prognostic Inference
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
                    Runs causal feature extraction and RobustScaler transformation strictly up to the chosen cycle.
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 12, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                      Observation Cycle:
                    </span>
                    <input
                      type="number"
                      min={1}
                      max={machine?.max_cycle || 300}
                      value={targetCycle}
                      onChange={(e) => setTargetCycle(parseInt(e.target.value) || 1)}
                      style={{
                        width: 80,
                        padding: "6px 8px",
                        borderRadius: 6,
                        border: "1px solid var(--border-default)",
                        backgroundColor: "var(--bg-surface)",
                        color: "var(--text-primary)",
                        fontSize: 12,
                        fontFamily: "var(--font-mono)",
                        textAlign: "center",
                      }}
                    />
                  </div>

                  <button
                    onClick={() => handleRunInference()}
                    disabled={isPredicting}
                    className="tech-btn tech-btn-primary"
                    style={{ fontSize: 12, padding: "8px 16px", display: "inline-flex", alignItems: "center", gap: 8 }}
                  >
                    <Gauge size={14} />
                    {isPredicting ? "Running Inference..." : "Run RUL Inference"}
                  </button>
                </div>
              </div>

              {predictFeedback && (
                <div
                  style={{
                    marginTop: 12,
                    padding: "8px 12px",
                    borderRadius: 6,
                    fontSize: 12,
                    backgroundColor: predictFeedback.type === "success" ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
                    border: `1px solid ${predictFeedback.type === "success" ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
                    color: predictFeedback.type === "success" ? "#10B981" : "#EF4444",
                  }}
                >
                  {predictFeedback.message}
                </div>
              )}
            </div>

            {/* Prediction History Table */}
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", marginBottom: 12 }}>
                Persisted Prognostic History & Trajectory ({predictionHistory.length} Inferences)
              </div>

              {predictionHistory.length === 0 ? (
                <div style={{ color: "var(--text-muted)", fontSize: 12 }}>No historical predictions saved for this asset.</div>
              ) : (
                <div style={{ overflowX: "auto" }}>
                  <table className="tech-table">
                    <thead>
                      <tr>
                        <th>Observation Cycle</th>
                        <th>Estimated RUL</th>
                        <th>Health Index</th>
                        <th>Analytical State</th>
                        <th>Model Version</th>
                        <th>Inference Timestamp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {predictionHistory.map((p) => (
                        <tr key={p.id}>
                          <td style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>Cycle {p.observation_cycle}</td>
                          <td style={{ fontFamily: "var(--font-mono)", fontWeight: 700 }}>{p.predicted_rul.toFixed(1)} cyc</td>
                          <td style={{ fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>{p.health_index.toFixed(3)}</td>
                          <td>
                            <StatusBadge status={p.operational_state} />
                          </td>
                          <td style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>{p.model_version}</td>
                          <td style={{ fontSize: 11, color: "var(--text-muted)" }}>
                            {new Date(p.created_at).toLocaleDateString()} {new Date(p.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Risk Assessment & Policy History Section */}
            <div style={{ marginTop: 28 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)", marginBottom: 12 }}>
                Deterministic Risk Assessments & Policy Trace ({riskHistory.length} Recorded)
              </div>

              {riskHistory.length === 0 ? (
                <div style={{ color: "var(--text-muted)", fontSize: 12 }}>No historical risk assessments evaluated for this asset.</div>
              ) : (
                <div style={{ overflowX: "auto" }}>
                  <table className="tech-table">
                    <thead>
                      <tr>
                        <th>Risk State</th>
                        <th>Health Index</th>
                        <th>Predicted RUL</th>
                        <th>Reason Codes</th>
                        <th>Policy Version</th>
                        <th>Evaluated Timestamp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {riskHistory.map((r) => (
                        <tr key={r.id}>
                          <td>
                            <StatusBadge status={r.risk_state} />
                          </td>
                          <td style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: "var(--accent-cyan)" }}>
                            {r.health_index.toFixed(3)}
                          </td>
                          <td style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                            {r.predicted_rul.toFixed(1)} cyc
                          </td>
                          <td>
                            <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                              {r.reason_codes.map((code) => (
                                <span
                                  key={code}
                                  style={{
                                    fontSize: 10,
                                    fontFamily: "var(--font-mono)",
                                    backgroundColor: "rgba(255, 255, 255, 0.05)",
                                    padding: "2px 6px",
                                    borderRadius: 3,
                                  }}
                                >
                                  {code}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                            {r.policy_version}
                          </td>
                          <td style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                            {new Date(r.created_at).toLocaleDateString()} {new Date(r.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Evidence Lineage (Milestone M8) */}
        {activeTab === "evidence" && (
          <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
            {/* Header / Domain Separation Notice */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: 12,
                padding: "14px 18px",
                backgroundColor: "rgba(0, 229, 255, 0.05)",
                border: "1px solid rgba(0, 229, 255, 0.2)",
                borderRadius: "var(--radius-sm)",
              }}
            >
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: "var(--accent-cyan)", display: "flex", alignItems: "center", gap: 8 }}>
                  <Activity size={16} />
                  MACHINE HEALTH EVIDENCE TIMELINE — C-MAPSS FD001
                </div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 2 }}>
                  Authoritative causal lineage: Telemetry Cycle → Features → RUL Prediction → Health Index → Risk Assessment → Alert.
                </div>
              </div>
              <div
                style={{
                  fontSize: 10,
                  fontFamily: "var(--font-mono)",
                  color: "var(--accent-amber)",
                  backgroundColor: "rgba(245, 158, 11, 0.1)",
                  padding: "4px 8px",
                  borderRadius: 4,
                  border: "1px solid rgba(245, 158, 11, 0.25)",
                }}
              >
                STRICT DOMAIN SEPARATION: VISUAL INSPECTION (MVTEC) IS EXCLUDED
              </div>
            </div>

            {/* Evidence Chain Component */}
            {latestRisk && <EvidenceChain assessment={latestRisk} />}

            {/* Timeline Stream */}
            <div
              style={{
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--border-default)",
                borderRadius: "var(--radius-sm)",
                padding: 20,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
                  Persisted Evidence Records for {id} ({evidenceTimeline.length})
                </span>
                <Link
                  href="/evidence?domain=MACHINE_HEALTH"
                  style={{
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                    color: "var(--accent-cyan)",
                    textDecoration: "none",
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                  }}
                >
                  OPEN IN EVIDENCE WORKSPACE <ArrowRight size={12} />
                </Link>
              </div>

              {isLoadingEvidence ? (
                <div style={{ textAlign: "center", padding: 32, color: "var(--text-muted)", fontSize: 12 }}>
                  Querying immutable evidence ledger...
                </div>
              ) : evidenceTimeline.length === 0 ? (
                <div style={{ textAlign: "center", padding: 32, color: "var(--text-muted)", fontSize: 12 }}>
                  No evidence records materialized yet for this asset. Run <code>materialize_evidence.py</code> to index persisted records.
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {evidenceTimeline.map((ev) => (
                    <div
                      key={ev.id}
                      style={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: 14,
                        padding: "12px 14px",
                        backgroundColor: "rgba(0, 0, 0, 0.25)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "var(--radius-sm)",
                      }}
                    >
                      <div
                        style={{
                          padding: "4px 8px",
                          borderRadius: 4,
                          fontSize: 10,
                          fontFamily: "var(--font-mono)",
                          fontWeight: 700,
                          backgroundColor:
                            ev.evidence_type === "ALERT"
                              ? "rgba(239, 68, 68, 0.15)"
                              : ev.evidence_type === "RISK_ASSESSMENT"
                              ? "rgba(245, 158, 11, 0.15)"
                              : ev.evidence_type === "RUL_PREDICTION"
                              ? "rgba(0, 229, 255, 0.15)"
                              : "rgba(255, 255, 255, 0.05)",
                          color:
                            ev.evidence_type === "ALERT"
                              ? "var(--accent-red)"
                              : ev.evidence_type === "RISK_ASSESSMENT"
                              ? "var(--accent-amber)"
                              : ev.evidence_type === "RUL_PREDICTION"
                              ? "var(--accent-cyan)"
                              : "var(--text-secondary)",
                          minWidth: 120,
                          textAlign: "center",
                        }}
                      >
                        {ev.evidence_type}
                      </div>

                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                          <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--accent-cyan)", fontWeight: 600 }}>
                            Cycle {ev.observation_cycle ?? "—"}
                          </span>
                          <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                            Source: {ev.source}
                          </span>
                          <span
                            style={{
                              fontSize: 10,
                              fontFamily: "var(--font-mono)",
                              padding: "1px 6px",
                              borderRadius: 3,
                              backgroundColor: "rgba(255,255,255,0.06)",
                              color: "var(--text-muted)",
                            }}
                          >
                            {ev.quality_state}
                          </span>
                        </div>

                        {ev.explanation && (
                          <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4, lineHeight: 1.4 }}>
                            {ev.explanation}
                          </div>
                        )}
                      </div>

                      <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)", textAlign: "right" }}>
                        {new Date(ev.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab: Maintenance Work Orders (M9) */}
        {activeTab === "maintenance" && (
          <div style={{ padding: 20 }}>
            {/* Domain Safety & Context Banner */}
            <div
              style={{
                padding: "12px 16px",
                backgroundColor: "rgba(56, 189, 248, 0.06)",
                border: "1px solid rgba(56, 189, 248, 0.2)",
                borderRadius: "var(--radius-sm)",
                fontSize: 12,
                color: "var(--text-secondary)",
                marginBottom: 20,
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: 12,
              }}
            >
              <div>
                <strong style={{ color: "var(--accent-cyan)", fontFamily: "var(--font-mono)" }}>
                  MACHINE HEALTH MAINTENANCE WORKFLOW:
                </strong>{" "}
                Operational work items grounded in C-MAPSS FD001 sensor prognostics and analytical risk states. Strict domain separation prohibits cross-domain causality with optical inspection.
              </div>
              <Link
                href="/maintenance"
                style={{
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  fontWeight: 600,
                  color: "var(--accent-cyan)",
                  textDecoration: "underline",
                }}
              >
                OPEN MAINTENANCE WORKSPACE →
              </Link>
            </div>

            {/* Draft from Latest Risk Action Card */}
            {latestRisk && latestRisk.risk_state !== "NORMAL" && (
              <div
                style={{
                  padding: "14px 18px",
                  backgroundColor: "rgba(234, 179, 8, 0.08)",
                  border: "1px solid rgba(234, 179, 8, 0.3)",
                  borderRadius: "var(--radius-sm)",
                  marginBottom: 20,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: 12,
                }}
              >
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, fontFamily: "var(--font-mono)", color: "#FACC15", marginBottom: 2 }}>
                    ACTIVE OPERATIONAL RISK DETECTED ({latestRisk.risk_state})
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-primary)" }}>
                    RUL: {latestRisk.predicted_rul.toFixed(1)} cycles | Health Index: {latestRisk.health_index.toFixed(3)} | Reason: {latestRisk.explanation}
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  {draftMsg && (
                    <span style={{ fontSize: 11, color: draftMsg.type === "success" ? "var(--risk-normal)" : "var(--risk-critical)", fontFamily: "var(--font-mono)" }}>
                      {draftMsg.text}
                    </span>
                  )}
                  <button
                    onClick={handleDraftMaintenanceFromRisk}
                    disabled={isDraftingRecommendation}
                    className="btn btn-primary"
                    style={{ padding: "8px 14px", fontSize: 11, fontFamily: "var(--font-mono)" }}
                  >
                    {isDraftingRecommendation ? "DRAFTING..." : "DRAFT RECOMMENDATION WORK ORDER"}
                  </button>
                </div>
              </div>
            )}

            {/* Active & Completed Orders List */}
            {isLoadingMaintenance ? (
              <div style={{ padding: 24 }}>
                <div style={{ color: "var(--text-muted)", fontSize: 12, fontFamily: "var(--font-mono)" }}>
                  Loading maintenance records...
                </div>
              </div>
            ) : maintenanceOrders.length === 0 ? (
              <EmptyState
                icon="database"
                metadataTag="MAINTENANCE WORKFLOW"
                title="No Maintenance Orders for Asset"
                description={`Asset ${machine?.machine_id} currently has no active or archived maintenance work orders. When sensor prognostics indicate elevated risk, recommendations can be generated deterministically.`}
              />
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, textAlign: "left" }}>
                  <thead>
                    <tr
                      style={{
                        borderBottom: "1px solid var(--border-default)",
                        color: "var(--text-muted)",
                        fontSize: 11,
                        fontFamily: "var(--font-mono)",
                        backgroundColor: "rgba(0,0,0,0.2)",
                      }}
                    >
                      <th style={{ padding: "10px 14px" }}>PRIORITY</th>
                      <th style={{ padding: "10px 14px" }}>STATUS</th>
                      <th style={{ padding: "10px 14px" }}>TITLE</th>
                      <th style={{ padding: "10px 14px" }}>RECOMMENDED ACTION</th>
                      <th style={{ padding: "10px 14px" }}>CREATED</th>
                      <th style={{ padding: "10px 14px", textAlign: "right" }}>WORK ORDER</th>
                    </tr>
                  </thead>
                  <tbody>
                    {maintenanceOrders.map((wo) => (
                      <tr
                        key={wo.id}
                        style={{
                          borderBottom: "1px solid var(--border-subtle)",
                        }}
                      >
                        <td style={{ padding: "12px 14px" }}>
                          <span
                            style={{
                              padding: "2px 8px",
                              borderRadius: "var(--radius-sm)",
                              fontSize: 10,
                              fontWeight: 700,
                              fontFamily: "var(--font-mono)",
                              border: `1px solid ${
                                wo.priority === "CRITICAL"
                                  ? "var(--risk-critical)"
                                  : wo.priority === "HIGH"
                                  ? "var(--risk-elevated)"
                                  : "#EAB308"
                              }`,
                              color:
                                wo.priority === "CRITICAL"
                                  ? "var(--risk-critical)"
                                  : wo.priority === "HIGH"
                                  ? "var(--risk-elevated)"
                                  : "#EAB308",
                            }}
                          >
                            {wo.priority}
                          </span>
                        </td>
                        <td style={{ padding: "12px 14px" }}>
                          <span
                            style={{
                              padding: "2px 8px",
                              borderRadius: "var(--radius-sm)",
                              fontSize: 10,
                              fontWeight: 600,
                              fontFamily: "var(--font-mono)",
                              color:
                                wo.status === "COMPLETED"
                                  ? "var(--risk-normal)"
                                  : wo.status === "IN_PROGRESS"
                                  ? "#FACC15"
                                  : "var(--accent-cyan)",
                            }}
                          >
                            {wo.status}
                          </span>
                        </td>
                        <td style={{ padding: "12px 14px", fontWeight: 600, color: "var(--text-primary)" }}>
                          {wo.title}
                          {wo.resolution_notes && (
                            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                              Outcome: {wo.resolution_notes}
                            </div>
                          )}
                        </td>
                        <td style={{ padding: "12px 14px", color: "var(--text-secondary)", maxWidth: 350 }}>
                          {wo.recommended_action}
                        </td>
                        <td style={{ padding: "12px 14px", fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
                          {new Date(wo.created_at).toLocaleDateString()}
                        </td>
                        <td style={{ padding: "12px 14px", textAlign: "right" }}>
                          <Link
                            href="/maintenance"
                            className="btn btn-secondary"
                            style={{ padding: "4px 8px", fontSize: 11, fontFamily: "var(--font-mono)", textDecoration: "none" }}
                          >
                            VIEW IN QUEUE →
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Sensor Statistics Matrix */}
        {activeTab === "stats" && summary && (
          <div style={{ padding: 20 }}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, textAlign: "left" }}>
                <thead>
                  <tr
                    style={{
                      borderBottom: "1px solid var(--border-default)",
                      fontFamily: "var(--font-mono)",
                      color: "var(--text-muted)",
                      fontSize: 11,
                    }}
                  >
                    <th style={{ padding: "10px 12px" }}>CHANNEL KEY</th>
                    <th style={{ padding: "10px 12px" }}>ENGINEERING NAME</th>
                    <th style={{ padding: "10px 12px" }}>UNIT</th>
                    <th style={{ padding: "10px 12px" }}>CYCLE 1 START</th>
                    <th style={{ padding: "10px 12px" }}>CYCLE {summary.latest_cycle} FINAL</th>
                    <th style={{ padding: "10px 12px" }}>NET DRIFT (Δ)</th>
                    <th style={{ padding: "10px 12px" }}>% DRIFT</th>
                    <th style={{ padding: "10px 12px" }}>DIRECTION</th>
                    <th style={{ padding: "10px 12px" }}>MEAN [MIN, MAX]</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.sensors.map((s) => (
                    <tr
                      key={s.sensor_key}
                      style={{
                        borderBottom: "1px solid var(--border-subtle)",
                        fontFamily: "var(--font-mono)",
                      }}
                    >
                      <td style={{ padding: "10px 12px", color: "var(--accent-cyan)", fontWeight: 600 }}>
                        {s.sensor_key}
                      </td>
                      <td style={{ padding: "10px 12px", color: "var(--text-primary)" }}>
                        {s.channel_name}
                      </td>
                      <td style={{ padding: "10px 12px", color: "var(--text-muted)" }}>
                        {s.engineering_unit}
                      </td>
                      <td style={{ padding: "10px 12px", color: "var(--text-secondary)" }}>
                        {s.initial_value.toFixed(3)}
                      </td>
                      <td style={{ padding: "10px 12px", color: "var(--text-primary)", fontWeight: 600 }}>
                        {s.latest_value.toFixed(3)}
                      </td>
                      <td
                        style={{
                          padding: "10px 12px",
                          fontWeight: 600,
                          color: s.net_change > 0 ? "var(--risk-critical)" : "var(--accent-cyan)",
                        }}
                      >
                        {s.net_change > 0 ? `+${s.net_change.toFixed(3)}` : s.net_change.toFixed(3)}
                      </td>
                      <td style={{ padding: "10px 12px" }}>
                        {s.pct_change !== null ? (
                          <span
                            style={{
                              color: Math.abs(s.pct_change) > 1.5 ? "var(--risk-critical)" : "var(--text-secondary)",
                            }}
                          >
                            {s.pct_change > 0 ? `+${s.pct_change.toFixed(2)}%` : `${s.pct_change.toFixed(2)}%`}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td style={{ padding: "10px 12px" }}>
                        <span
                          style={{
                            display: "inline-block",
                            padding: "2px 6px",
                            borderRadius: "var(--radius-xs)",
                            fontSize: 10,
                            backgroundColor:
                              s.direction === "INCREASING"
                                ? "rgba(239, 68, 68, 0.1)"
                                : s.direction === "DECREASING"
                                ? "rgba(0, 229, 255, 0.1)"
                                : "rgba(255, 255, 255, 0.05)",
                            color:
                              s.direction === "INCREASING"
                                ? "var(--risk-critical)"
                                : s.direction === "DECREASING"
                                ? "var(--accent-cyan)"
                                : "var(--text-muted)",
                          }}
                        >
                          {s.direction}
                        </span>
                      </td>
                      <td style={{ padding: "10px 12px", color: "var(--text-muted)", fontSize: 11 }}>
                        {s.mean_value.toFixed(2)} [{s.min_value.toFixed(2)}, {s.max_value.toFixed(2)}]
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 3: Sensor Correlation Matrix */}
        {activeTab === "correlation" && correlation && (
          <div style={{ padding: 20 }}>
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                Active Sensor Bivariate Correlation Matrix (Pearson r)
              </div>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
                Calculated across all {summary?.total_cycles} cycles for this engine. Values range from -1.0 (inverse correlation) to +1.0 (direct correlation). Correlation does not imply physical causality.
              </div>
            </div>

            <div style={{ overflowX: "auto" }}>
              <table style={{ borderCollapse: "collapse", fontSize: 11, fontFamily: "var(--font-mono)" }}>
                <thead>
                  <tr>
                    <th style={{ padding: "6px 10px", color: "var(--text-muted)", textAlign: "left" }}>CHANNEL</th>
                    {correlation.channels.map((c) => (
                      <th key={c} style={{ padding: "6px 8px", color: "var(--accent-cyan)", textAlign: "center" }}>
                        {c.replace("sensor_", "S")}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {correlation.matrix.map((row, i) => (
                    <tr key={correlation.channels[i]}>
                      <td style={{ padding: "6px 10px", color: "var(--text-secondary)", fontWeight: 600, whiteSpace: "nowrap" }}>
                        {correlation.channels[i].replace("sensor_", "Sensor ")} ({correlation.channel_names[i].split("(")[1]?.replace(")", "") || ""})
                      </td>
                      {row.map((val, j) => {
                        const isDiag = i === j;
                        // Color interpolate: -1.0 (blue) -> 0.0 (dark) -> 1.0 (cyan)
                        let bg = "rgba(255, 255, 255, 0.02)";
                        let textColor = "var(--text-muted)";
                        if (val > 0.4) {
                          bg = `rgba(0, 229, 255, ${Math.min(0.35, val * 0.35)})`;
                          textColor = "var(--accent-cyan)";
                        } else if (val < -0.4) {
                          bg = `rgba(59, 130, 246, ${Math.min(0.35, Math.abs(val) * 0.35)})`;
                          textColor = "#93C5FD";
                        }
                        if (isDiag) {
                          bg = "rgba(0, 229, 255, 0.15)";
                          textColor = "#FFF";
                        }

                        return (
                          <td
                            key={j}
                            style={{
                              padding: "6px 8px",
                              textAlign: "center",
                              backgroundColor: bg,
                              color: textColor,
                              border: "1px solid var(--border-subtle)",
                              fontWeight: isDiag ? 700 : 400,
                            }}
                          >
                            {val.toFixed(2)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 4: ML Feature Preview */}
        {activeTab === "features" && features && (
          <div style={{ padding: 20 }}>
            {/* Disclaimer Banner */}
            <div
              style={{
                padding: "14px 18px",
                backgroundColor: "rgba(0, 229, 255, 0.06)",
                border: "1px solid rgba(0, 229, 255, 0.25)",
                borderRadius: "var(--radius-sm)",
                marginBottom: 20,
                display: "flex",
                alignItems: "flex-start",
                gap: 12,
              }}
            >
              <Info size={18} color="var(--accent-cyan)" style={{ marginTop: 2, flexShrink: 0 }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: "var(--accent-cyan)", fontFamily: "var(--font-mono)" }}>
                  PHASE 4 ML HANDOFF CONTRACT (DERIVED FEATURES ONLY)
                </div>
                <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4, lineHeight: 1.5 }}>
                  {features.disclaimer} Each row represents a 96-dimensional causal feature vector computed from the trailing W={features.window_size} cycles.
                  Scalers will be fitted exclusively on `INTERNAL_TRAIN` (Units 1–80) during Milestone M4.
                </div>
              </div>
            </div>

            <div style={{ overflowX: "auto", maxHeight: 360, overflowY: "auto", border: "1px solid var(--border-default)", borderRadius: "var(--radius-xs)" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11, fontFamily: "var(--font-mono)", textAlign: "left" }}>
                <thead style={{ position: "sticky", top: 0, backgroundColor: "var(--bg-app)", borderBottom: "1px solid var(--border-default)", color: "var(--text-muted)" }}>
                  <tr>
                    <th style={{ padding: "8px 12px" }}>CYCLE</th>
                    <th style={{ padding: "8px 12px" }}>T24 RAW</th>
                    <th style={{ padding: "8px 12px", color: "var(--accent-cyan)" }}>T24 ROLLING MEAN</th>
                    <th style={{ padding: "8px 12px" }}>T24 ROLLING STD</th>
                    <th style={{ padding: "8px 12px" }}>T24 SLOPE</th>
                    <th style={{ padding: "8px 12px" }}>T30 ROLLING MEAN</th>
                    <th style={{ padding: "8px 12px" }}>P30 ROLLING MEAN</th>
                    <th style={{ padding: "8px 12px" }}>NF ROLLING MEAN</th>
                  </tr>
                </thead>
                <tbody>
                  {features.rows.map((row) => (
                    <tr key={row.cycle} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                      <td style={{ padding: "8px 12px", fontWeight: 700, color: "var(--text-primary)" }}>#{row.cycle}</td>
                      <td style={{ padding: "8px 12px", color: "var(--text-secondary)" }}>{row.features["sensor_2_raw"]?.toFixed(3)}</td>
                      <td style={{ padding: "8px 12px", color: "var(--accent-cyan)", fontWeight: 600 }}>{row.features["sensor_2_rolling_mean_w20"]?.toFixed(3)}</td>
                      <td style={{ padding: "8px 12px", color: "var(--text-secondary)" }}>{row.features["sensor_2_rolling_std_w20"]?.toFixed(3)}</td>
                      <td style={{ padding: "8px 12px", color: "var(--text-primary)" }}>{row.features["sensor_2_rolling_slope_w20"]?.toFixed(5)}</td>
                      <td style={{ padding: "8px 12px", color: "var(--text-secondary)" }}>{row.features["sensor_3_rolling_mean_w20"]?.toFixed(2)}</td>
                      <td style={{ padding: "8px 12px", color: "var(--text-secondary)" }}>{row.features["sensor_7_rolling_mean_w20"]?.toFixed(2)}</td>
                      <td style={{ padding: "8px 12px", color: "var(--text-secondary)" }}>{row.features["sensor_8_rolling_mean_w20"]?.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 5: Asset Comparison */}
        {activeTab === "compare" && (
          <div style={{ padding: 20 }}>
            {/* Compare Target Selector */}
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
              <span style={{ fontSize: 12, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                COMPARE WITH ASSET:
              </span>
              <select
                value={compareTargetId}
                onChange={(e) => setCompareTargetId(e.target.value)}
                style={{
                  padding: "7px 12px",
                  backgroundColor: "var(--bg-app)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-sm)",
                  color: "var(--accent-cyan)",
                  fontSize: 12,
                  fontFamily: "var(--font-mono)",
                  outline: "none",
                }}
              >
                {["TURBOFAN-ENG-002", "TURBOFAN-ENG-003", "TURBOFAN-ENG-010", "TURBOFAN-ENG-085", "TURBOFAN-ENG-TEST-001"].map((mid) => (
                  <option key={mid} value={mid}>{mid}</option>
                ))}
              </select>
            </div>

            {comparison && comparison.machines.length >= 2 ? (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, fontFamily: "var(--font-mono)", textAlign: "left" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border-default)", color: "var(--text-muted)", fontSize: 11 }}>
                      <th style={{ padding: "10px 12px" }}>METRIC</th>
                      {comparison.machines.map((m) => (
                        <th key={m.machine_id} style={{ padding: "10px 12px", color: "var(--accent-cyan)" }}>
                          {m.machine_id}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                      <td style={{ padding: "10px 12px", color: "var(--text-muted)" }}>Split Allocation</td>
                      {comparison.machines.map((m) => (
                        <td key={m.machine_id} style={{ padding: "10px 12px" }}>{m.split_category}</td>
                      ))}
                    </tr>
                    <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                      <td style={{ padding: "10px 12px", color: "var(--text-muted)" }}>Total Operational Cycles</td>
                      {comparison.machines.map((m) => (
                        <td key={m.machine_id} style={{ padding: "10px 12px", fontWeight: 700 }}>{m.total_cycles} cycles</td>
                      ))}
                    </tr>
                    <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                      <td style={{ padding: "10px 12px", color: "var(--text-muted)" }}>Net T24 Temp Drift (Δ °R)</td>
                      {comparison.machines.map((m) => (
                        <td key={m.machine_id} style={{ padding: "10px 12px", color: "var(--accent-cyan)" }}>{m.drift_t24 > 0 ? `+${m.drift_t24}` : m.drift_t24}</td>
                      ))}
                    </tr>
                    <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                      <td style={{ padding: "10px 12px", color: "var(--text-muted)" }}>Net T30 Temp Drift (Δ °R)</td>
                      {comparison.machines.map((m) => (
                        <td key={m.machine_id} style={{ padding: "10px 12px", color: "var(--risk-critical)" }}>{m.drift_t30 > 0 ? `+${m.drift_t30}` : m.drift_t30}</td>
                      ))}
                    </tr>
                    <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                      <td style={{ padding: "10px 12px", color: "var(--text-muted)" }}>Net P30 Pressure Drift (Δ psia)</td>
                      {comparison.machines.map((m) => (
                        <td key={m.machine_id} style={{ padding: "10px 12px" }}>{m.drift_p30}</td>
                      ))}
                    </tr>
                    <tr style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                      <td style={{ padding: "10px 12px", color: "var(--text-muted)" }}>Mean Thermal Volatility (σ)</td>
                      {comparison.machines.map((m) => (
                        <td key={m.machine_id} style={{ padding: "10px 12px", color: "var(--text-secondary)" }}>{m.volatility_score}</td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ color: "var(--text-muted)", fontSize: 12, padding: 20 }}>
                Select a valid target machine to compare operational drift metrics.
              </div>
            )}
          </div>
        )}
      </div>

      {/* Invariant Channels Card */}
      <div
        style={{
          padding: "16px 20px",
          backgroundColor: "rgba(255, 255, 255, 0.02)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-sm)",
          display: "flex",
          alignItems: "flex-start",
          gap: 14,
        }}
      >
        <Info size={18} color="var(--accent-cyan)" style={{ marginTop: 2, flexShrink: 0 }} />
        <div style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.6 }}>
          <strong style={{ color: "var(--text-primary)" }}>Milestone M3 Analytics & Feature Engineering:</strong>
          {" "}Rolling window features ($W=20$) are strictly causal and computed from actual C-MAPSS telemetry persisted in PostgreSQL.
          The 7 invariant channels (`op_setting_3`, `sensor_1, 5, 10, 16, 18, 19`) are excluded from active feature vectors.
          Zero ML predictions, RUL estimations, or risk states are synthesized.
        </div>
      </div>
    </AppShell>
  );
}
