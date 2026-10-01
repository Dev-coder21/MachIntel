"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { StatusBadge } from "@/components/common/StatusBadge";
import { apiClient } from "@/lib/api-client";
import { ModelRegistryItem, ModelRegistryListResponse } from "@/types/model";
import { FleetPrognosticsOverview, PredictionItem } from "@/types/prediction";
import { MachineListResponse } from "@/types/machine";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  CheckCircle,
  Clock,
  Cpu,
  Database,
  ExternalLink,
  Flame,
  Gauge,
  HelpCircle,
  Info,
  Layers,
  LineChart,
  Search,
  ShieldAlert,
  Sparkles,
  TrendingDown,
  Zap,
} from "lucide-react";

export default function PredictionsPage() {
  const [fleetOverview, setFleetOverview] = useState<FleetPrognosticsOverview | null>(null);
  const [models, setModels] = useState<ModelRegistryItem[]>([]);
  const [activeModelId, setActiveModelId] = useState<string | null>(null);
  const [predictions, setPredictions] = useState<PredictionItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [filterState, setFilterState] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        const [overviewRes, modelsRes, machinesRes] = await Promise.all([
          apiClient.getFleetPrognosticsOverview(),
          apiClient.getModels(),
          apiClient.getMachines({ limit: 100 }),
        ]);

        setFleetOverview(overviewRes);
        setModels(modelsRes.items);
        setActiveModelId(modelsRes.active_model_id ?? null);

        // Fetch latest predictions for the first batch of machines
        const predPromises = machinesRes.items.slice(0, 50).map(async (m) => {
          try {
            return await apiClient.getMachineLatestPrediction(m.machine_id);
          } catch {
            return null;
          }
        });

        const resolvedPreds = (await Promise.all(predPromises)).filter(
          (p): p is PredictionItem => p !== null
        );
        setPredictions(resolvedPreds);
      } catch (err) {
        console.error("Failed to load prognostics data", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  const activeModel = models.find((m) => m.model_id === activeModelId) || models[0];

  const filteredPredictions = predictions.filter((p) => {
    const matchesState = filterState === "ALL" || p.operational_state === filterState;
    const matchesSearch =
      searchQuery === "" ||
      p.machine_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.model_version.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesState && matchesSearch;
  });

  return (
    <AppShell>
      <PageHeader
        title="Prognostics & Remaining Useful Life (RUL)"
        subtitle="Empirical machine degradation modeling, causal multi-channel regression, and analytical health states."
        badge={<StatusBadge status="ACTIVE" label="PRODUCTION PROGNOSTICS • ACTIVE" />}
      />

      {/* Analytical Risk Disclaimer & Data Tier Formulation Banner */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 12,
          padding: "16px 20px",
          borderRadius: "var(--radius-md)",
          backgroundColor: "rgba(0, 229, 255, 0.04)",
          border: "1px solid rgba(0, 229, 255, 0.2)",
          marginBottom: 24,
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
          <Info size={18} color="var(--accent-cyan)" style={{ marginTop: 2, flexShrink: 0 }} />
          <div style={{ fontSize: 13, lineHeight: 1.5, color: "var(--text-secondary)" }}>
            <strong style={{ color: "var(--text-primary)" }}>Analytical Risk Formulation Notice: </strong>
            Remaining Useful Life values are estimated via empirical statistical regression on NASA C-MAPSS FD001 run-to-failure telemetry.
            Operational states are deterministic analytical risk interpretations (<code style={{ fontFamily: "var(--font-mono)", color: "var(--accent-cyan)" }}>HI = clamp(RUL / 125, 0, 1)</code>).
            They reflect decision-support risk categorization rather than guaranteed failure determinations.
          </div>
        </div>

        {/* 4-Tier Data Classification Architecture */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: 10,
            paddingTop: 12,
            borderTop: "1px solid rgba(0, 229, 255, 0.1)",
            fontSize: 11,
            fontFamily: "var(--font-mono)",
          }}
        >
          <div>
            <span style={{ color: "var(--accent-cyan)", fontWeight: 700 }}>1. OBSERVED:</span>
            <div style={{ color: "var(--text-muted)", marginTop: 2 }}>17 active sensor channels across operational flight cycles</div>
          </div>
          <div>
            <span style={{ color: "var(--accent-cyan)", fontWeight: 700 }}>2. DERIVED:</span>
            <div style={{ color: "var(--text-muted)", marginTop: 2 }}>102 rolling statistical features (causal window W=20)</div>
          </div>
          <div>
            <span style={{ color: "var(--accent-cyan)", fontWeight: 700 }}>3. MODEL OUTPUT:</span>
            <div style={{ color: "var(--text-muted)", marginTop: 2 }}>Estimated RUL (clamped at 125) & Health Index (0.0–1.0)</div>
          </div>
          <div>
            <span style={{ color: "var(--accent-cyan)", fontWeight: 700 }}>4. POLICY:</span>
            <div style={{ color: "var(--text-muted)", marginTop: 2 }}>Risk state mapping (NORMAL, WATCH, ELEVATED, CRITICAL)</div>
          </div>
        </div>
      </div>

      {/* Fleet Prognostics Metric Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 16,
          marginBottom: 24,
        }}
      >
        <div className="tech-card">
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
            <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>ACTIVE MODEL</span>
            <Cpu size={16} color="var(--accent-cyan)" />
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-cyan)", marginBottom: 4 }}>
            {fleetOverview?.active_model_algorithm || "Random Forest"}
          </div>
          <div style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
            {fleetOverview?.active_model_id || "rul-randomforest-v1.0.0"}
          </div>
        </div>

        <div className="tech-card">
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
            <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>PREDICTION COVERAGE</span>
            <Activity size={16} color="#10B981" />
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-primary)", marginBottom: 4 }}>
            {fleetOverview ? `${fleetOverview.machines_with_predictions} / ${fleetOverview.total_machines}` : "..."}
          </div>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
            {fleetOverview && fleetOverview.total_machines > 0
              ? `${Math.round((fleetOverview.machines_with_predictions / fleetOverview.total_machines) * 100)}% fleet coverage`
              : "Ingested engines"}
          </div>
        </div>

        <div className="tech-card">
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
            <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>FLEET AVG ESTIMATED RUL</span>
            <Clock size={16} color="#F59E0B" />
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-primary)", marginBottom: 4 }}>
            {fleetOverview?.average_predicted_rul !== null && fleetOverview?.average_predicted_rul !== undefined
              ? `${fleetOverview.average_predicted_rul} cyc`
              : "..."}
          </div>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
            Capped at RUL_max = 125 cycles
          </div>
        </div>

        <div className="tech-card">
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
            <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>FLEET AVG HEALTH INDEX</span>
            <Gauge size={16} color="#8B5CF6" />
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-primary)", marginBottom: 4 }}>
            {fleetOverview?.average_health_index !== null && fleetOverview?.average_health_index !== undefined
              ? fleetOverview.average_health_index.toFixed(3)
              : "..."}
          </div>
          <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
            Scale: 0.0 (Failed) to 1.0 (Nominal)
          </div>
        </div>
      </div>

      {/* Health State Distribution Cards */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-muted)", marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          Fleet Analytical Health State Distribution
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
          <div
            onClick={() => setFilterState(filterState === "NORMAL" ? "ALL" : "NORMAL")}
            style={{
              padding: "14px 16px",
              borderRadius: 8,
              backgroundColor: "rgba(16, 185, 129, 0.06)",
              border: `1px solid ${filterState === "NORMAL" ? "#10B981" : "rgba(16, 185, 129, 0.25)"}`,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: "#10B981" }}>NORMAL (HI ≥ 0.70)</span>
              <CheckCircle size={15} color="#10B981" />
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>
              {fleetOverview?.state_distribution?.NORMAL ?? 0}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Nominal baseline health</div>
          </div>

          <div
            onClick={() => setFilterState(filterState === "WATCH" ? "ALL" : "WATCH")}
            style={{
              padding: "14px 16px",
              borderRadius: 8,
              backgroundColor: "rgba(6, 182, 212, 0.06)",
              border: `1px solid ${filterState === "WATCH" ? "#06B6D4" : "rgba(6, 182, 212, 0.25)"}`,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: "#06B6D4" }}>WATCH (0.40 ≤ HI &lt; 0.70)</span>
              <Activity size={15} color="#06B6D4" />
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>
              {fleetOverview?.state_distribution?.WATCH ?? 0}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Incipient wear trajectory</div>
          </div>

          <div
            onClick={() => setFilterState(filterState === "ELEVATED" ? "ALL" : "ELEVATED")}
            style={{
              padding: "14px 16px",
              borderRadius: 8,
              backgroundColor: "rgba(245, 158, 11, 0.06)",
              border: `1px solid ${filterState === "ELEVATED" ? "#F59E0B" : "rgba(245, 158, 11, 0.25)"}`,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: "#F59E0B" }}>ELEVATED (0.15 ≤ HI &lt; 0.40)</span>
              <AlertTriangle size={15} color="#F59E0B" />
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>
              {fleetOverview?.state_distribution?.ELEVATED ?? 0}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Substantial degradation</div>
          </div>

          <div
            onClick={() => setFilterState(filterState === "CRITICAL" ? "ALL" : "CRITICAL")}
            style={{
              padding: "14px 16px",
              borderRadius: 8,
              backgroundColor: "rgba(239, 68, 68, 0.06)",
              border: `1px solid ${filterState === "CRITICAL" ? "#EF4444" : "rgba(239, 68, 68, 0.25)"}`,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: "#EF4444" }}>CRITICAL (HI &lt; 0.15)</span>
              <ShieldAlert size={15} color="#EF4444" />
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>
              {fleetOverview?.state_distribution?.CRITICAL ?? 0}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Imminent end of cycle life</div>
          </div>
        </div>
      </div>

      {/* Model Evaluation & Benchmark Comparison Section */}
      <div className="tech-card" style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 8 }}>
              <BarChart3 size={18} color="var(--accent-cyan)" />
              Baseline Model Evaluation & Official Test Benchmarks
            </div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>
              Deterministic evaluation on NASA C-MAPSS FD001. Selection Rule: Lowest validation RMSE selects the active model.
            </div>
          </div>
          <div
            style={{
              padding: "4px 10px",
              borderRadius: 6,
              fontSize: 11,
              fontFamily: "var(--font-mono)",
              backgroundColor: "rgba(0, 229, 255, 0.1)",
              border: "1px solid rgba(0, 229, 255, 0.3)",
              color: "var(--accent-cyan)",
            }}
          >
            PRE-DEFINED SELECTION RULE ENFORCED
          </div>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table className="tech-table">
            <thead>
              <tr>
                <th>Model Identifier</th>
                <th>Algorithm</th>
                <th>Training Split</th>
                <th>Val RMSE</th>
                <th>Val PHM Score</th>
                <th>Test RMSE</th>
                <th>Test PHM Score</th>
                <th>Deployment Status</th>
              </tr>
            </thead>
            <tbody>
              {models.map((m) => (
                <tr key={m.model_id} style={{ backgroundColor: m.is_active ? "rgba(0, 229, 255, 0.03)" : undefined }}>
                  <td style={{ fontFamily: "var(--font-mono)", fontWeight: 600, color: m.is_active ? "var(--accent-cyan)" : "var(--text-primary)" }}>
                    {m.model_id}
                  </td>
                  <td>{m.algorithm}</td>
                  <td style={{ fontSize: 12, color: "var(--text-secondary)" }}>Units 1–80 (Fit Scaler Only)</td>
                  <td style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>{m.metrics?.val_rmse?.toFixed(2) ?? "—"}</td>
                  <td style={{ fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
                    {m.metrics?.val_phm_score ? m.metrics.val_phm_score.toLocaleString() : "—"}
                  </td>
                  <td style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>{m.metrics?.test_rmse?.toFixed(2) ?? "—"}</td>
                  <td style={{ fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
                    {m.metrics?.test_phm_score ? m.metrics.test_phm_score.toLocaleString() : "—"}
                  </td>
                  <td>
                    {m.is_active ? (
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                          padding: "3px 8px",
                          borderRadius: 4,
                          fontSize: 11,
                          fontWeight: 600,
                          backgroundColor: "rgba(16, 185, 129, 0.15)",
                          color: "#10B981",
                          border: "1px solid rgba(16, 185, 129, 0.3)",
                        }}
                      >
                        <CheckCircle size={12} /> ACTIVE SERVING
                      </span>
                    ) : (
                      <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Benchmark Baseline</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Feature Importance Preview for Active Model */}
        {activeModel && activeModel.feature_importances && (
          <div style={{ marginTop: 20, paddingTop: 16, borderTop: "1px solid var(--border-color)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)" }}>
                Model Feature Importance (Top Predictors for {activeModel.algorithm})
              </div>
              <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                Note: Reflects statistical feature weighting, not guaranteed physical causality.
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 10 }}>
              {Object.entries(activeModel.feature_importances)
                .slice(0, 6)
                .map(([feat, imp]) => (
                  <div
                    key={feat}
                    style={{
                      padding: "8px 12px",
                      borderRadius: 6,
                      backgroundColor: "var(--bg-secondary)",
                      border: "1px solid var(--border-color)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                    }}
                  >
                    <span style={{ fontSize: 12, fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>{feat}</span>
                    <span style={{ fontSize: 12, fontFamily: "var(--font-mono)", fontWeight: 600, color: "var(--accent-cyan)" }}>
                      {(imp * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>

      {/* Fleet Inferences Table */}
      <div className="tech-card">
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: 16, marginBottom: 16 }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)" }}>
              Fleet Prognostic Inferences
            </div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
              Latest empirical RUL predictions and derived analytical health states across engines.
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ position: "relative", minWidth: 220 }}>
              <Search size={14} color="var(--text-muted)" style={{ position: "absolute", left: 10, top: 10 }} />
              <input
                type="text"
                placeholder="Search engine ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: "100%",
                  padding: "7px 10px 7px 30px",
                  borderRadius: 6,
                  border: "1px solid var(--border-color)",
                  backgroundColor: "var(--bg-secondary)",
                  color: "var(--text-primary)",
                  fontSize: 12,
                  fontFamily: "var(--font-mono)",
                }}
              />
            </div>

            <div style={{ display: "flex", gap: 6 }}>
              {["ALL", "NORMAL", "WATCH", "ELEVATED", "CRITICAL"].map((st) => (
                <button
                  key={st}
                  onClick={() => setFilterState(st)}
                  className={`tech-btn ${filterState === st ? "tech-btn-primary" : ""}`}
                  style={{ fontSize: 11, padding: "5px 10px" }}
                >
                  {st}
                </button>
              ))}
            </div>
          </div>
        </div>

        {filteredPredictions.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px 20px", color: "var(--text-muted)" }}>
            No predictions found matching current filter.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="tech-table">
              <thead>
                <tr>
                  <th>Machine Entity</th>
                  <th>Observed Cycle</th>
                  <th>Estimated Remaining Useful Life</th>
                  <th>Health Index</th>
                  <th>Analytical State</th>
                  <th>Model Version</th>
                  <th>Inference Timestamp</th>
                  <th style={{ textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredPredictions.map((pred) => (
                  <tr key={pred.id}>
                    <td style={{ fontWeight: 600, fontFamily: "var(--font-mono)", color: "var(--accent-cyan)" }}>
                      <Link href={`/machines/${pred.machine_name}`} style={{ color: "inherit", textDecoration: "none" }}>
                        {pred.machine_name}
                      </Link>
                    </td>
                    <td style={{ fontFamily: "var(--font-mono)" }}>Cycle {pred.observation_cycle}</td>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: 14 }}>
                          {pred.predicted_rul.toFixed(1)} cyc
                        </span>
                        <div
                          style={{
                            width: 60,
                            height: 6,
                            borderRadius: 3,
                            backgroundColor: "var(--bg-secondary)",
                            overflow: "hidden",
                          }}
                        >
                          <div
                            style={{
                              width: `${Math.min(100, (pred.predicted_rul / 125) * 100)}%`,
                              height: "100%",
                              backgroundColor:
                                pred.operational_state === "NORMAL"
                                  ? "#10B981"
                                  : pred.operational_state === "WATCH"
                                  ? "#06B6D4"
                                  : pred.operational_state === "ELEVATED"
                                  ? "#F59E0B"
                                  : "#EF4444",
                            }}
                          />
                        </div>
                      </div>
                    </td>
                    <td style={{ fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
                      {pred.health_index.toFixed(3)}
                    </td>
                    <td>
                      <StatusBadge status={pred.operational_state} />
                    </td>
                    <td style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                      {pred.model_version}
                    </td>
                    <td style={{ fontSize: 11, color: "var(--text-muted)" }}>
                      {new Date(pred.created_at).toLocaleDateString()} {new Date(pred.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <Link
                        href={`/machines/${pred.machine_name}`}
                        className="tech-btn"
                        style={{ fontSize: 11, padding: "4px 8px", display: "inline-flex", alignItems: "center", gap: 4 }}
                      >
                        Investigate <ExternalLink size={11} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppShell>
  );
}
