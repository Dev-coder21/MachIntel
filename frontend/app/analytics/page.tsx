"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { apiClient } from "@/lib/api-client";
import { InspectionRun } from "@/types/inspection";
import {
  ConfusionMatrixAnalytics,
  DefectClassAnalytics,
  InspectionRunAnalyticsSummary,
  InspectionRunProvenance,
  LocalizationAnalytics,
  RunComparison,
  ScoreDistribution,
} from "@/types/inspection-analytics";
import {
  AlertTriangle,
  BarChart2,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  ExternalLink,
  Eye,
  FileText,
  Filter,
  Layers,
  LineChart,
  RefreshCw,
  Sliders,
  Sparkles,
  TrendingDown,
  TrendingUp,
  XCircle,
  Zap,
} from "lucide-react";
import Link from "next/link";

export default function AnalyticsPage() {
  const [runs, setRuns] = useState<InspectionRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  // Analytics states
  const [summary, setSummary] = useState<InspectionRunAnalyticsSummary | null>(null);
  const [scoreDist, setScoreDist] = useState<ScoreDistribution | null>(null);
  const [defectAnalytics, setDefectAnalytics] = useState<DefectClassAnalytics | null>(null);
  const [confusionMatrix, setConfusionMatrix] = useState<ConfusionMatrixAnalytics | null>(null);
  const [localization, setLocalization] = useState<LocalizationAnalytics | null>(null);
  const [provenance, setProvenance] = useState<InspectionRunProvenance | null>(null);
  const [comparison, setComparison] = useState<RunComparison | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [analyticsLoading, setAnalyticsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // 1. Fetch available runs
  const fetchRuns = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getInspectionAnalyticsRuns();
      setRuns(data);
      if (data.length > 0 && !selectedRunId) {
        setSelectedRunId(data[0].id);
      }
    } catch (err: unknown) {
      console.error("Failed to load inspection runs:", err);
      setError(err instanceof Error ? err.message : "Failed to load inspection analytics runs.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
  }, []);

  // 2. Fetch all analytics for selected run
  useEffect(() => {
    if (!selectedRunId) return;

    const loadAnalytics = async () => {
      try {
        setAnalyticsLoading(true);
        const [sum, scores, defects, cm, loc, prov, comp] = await Promise.all([
          apiClient.getInspectionAnalyticsSummary(selectedRunId),
          apiClient.getInspectionAnalyticsScores(selectedRunId, 15),
          apiClient.getInspectionAnalyticsDefects(selectedRunId),
          apiClient.getInspectionAnalyticsConfusionMatrix(selectedRunId),
          apiClient.getInspectionAnalyticsLocalization(selectedRunId),
          apiClient.getInspectionAnalyticsProvenance(selectedRunId),
          apiClient.getInspectionAnalyticsComparison().catch(() => null),
        ]);

        setSummary(sum);
        setScoreDist(scores);
        setDefectAnalytics(defects);
        setConfusionMatrix(cm);
        setLocalization(loc);
        setProvenance(prov);
        setComparison(comp);
      } catch (err: unknown) {
        console.error("Failed to load detailed inspection analytics:", err);
        setError(err instanceof Error ? err.message : "Failed to load detailed inspection analytics.");
      } finally {
        setAnalyticsLoading(false);
      }
    };

    loadAnalytics();
  }, [selectedRunId]);

  return (
    <AppShell>
      <PageHeader
        title="Inspection Analytics"
        subtitle="Optical defect distribution, score variance modeling, false-positive/negative classification forensics, and run history."
        breadcrumbs={[{ label: "Intelligence" }, { label: "Inspection Analytics" }]}
        actions={
          <div style={{ display: "flex", gap: 10 }}>
            <Link
              href="/inspections"
              className="btn btn-secondary"
              style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}
            >
              <Eye size={14} /> Inspection Station
            </Link>
            <button
              onClick={fetchRuns}
              className="btn btn-secondary"
              style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}
            >
              <RefreshCw size={14} /> Refresh
            </button>
          </div>
        }
      />

      {error && (
        <div
          style={{
            padding: "12px 16px",
            backgroundColor: "rgba(239, 68, 68, 0.12)",
            border: "1px solid var(--accent-red)",
            borderRadius: "var(--radius-md)",
            color: "var(--accent-red)",
            fontSize: 13,
            marginBottom: 20,
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Domain Separation Notice */}
      <div
        style={{
          padding: "10px 14px",
          backgroundColor: "rgba(6, 182, 212, 0.06)",
          border: "1px solid rgba(6, 182, 212, 0.25)",
          borderRadius: "var(--radius-sm)",
          fontSize: 12,
          color: "var(--text-secondary)",
          marginBottom: 20,
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <span
          style={{
            fontSize: 10,
            fontWeight: 700,
            fontFamily: "var(--font-mono)",
            padding: "2px 6px",
            borderRadius: 3,
            backgroundColor: "rgba(6, 182, 212, 0.2)",
            color: "var(--accent-cyan)",
          }}
        >
          DOMAIN NOTICE
        </span>
        <span>
          Inspection Analytics models optical surface anomalies exclusively for the <strong>MVTec AD fastener benchmark</strong>. These visual analytics are decoupled from NASA C-MAPSS turbofan engine health telemetry.
        </span>
      </div>

      {/* Run Selector & Header Provenance */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.2fr 2fr",
          gap: 16,
          marginBottom: 20,
        }}
      >
        {/* Selector Card */}
        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-md)",
            padding: 16,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Inspection Run Selector
            </span>
            <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--accent-cyan)" }}>
              {runs.length} Persisted Runs
            </span>
          </div>
          <select
            value={selectedRunId || ""}
            onChange={(e) => setSelectedRunId(e.target.value)}
            disabled={loading || runs.length === 0}
            style={{
              width: "100%",
              backgroundColor: "var(--bg-app)",
              border: "1px solid var(--border-default)",
              color: "var(--text-primary)",
              padding: "10px 12px",
              borderRadius: "var(--radius-sm)",
              fontSize: 13,
              fontFamily: "var(--font-mono)",
              outline: "none",
            }}
          >
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                {new Date(r.created_at).toLocaleDateString()} — {r.category} ({r.total_images} imgs | {r.defect_count} defects | τ={r.threshold.toFixed(2)})
              </option>
            ))}
          </select>
          {summary && (
            <div style={{ marginTop: 12, fontSize: 11, color: "var(--text-muted)", display: "flex", justifyContent: "space-between" }}>
              <span>Run ID: <code style={{ color: "var(--accent-cyan)" }}>{summary.run_id.slice(0, 8)}...</code></span>
              <span>Executed: {new Date(summary.created_at).toLocaleTimeString()}</span>
            </div>
          )}
        </div>

        {/* Provenance Strip */}
        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-md)",
            padding: 16,
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 12,
          }}
        >
          <div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 4 }}>
              Dataset Provenance
            </div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
              MVTec AD
            </div>
            <div style={{ fontSize: 11, color: "var(--accent-cyan)", fontFamily: "var(--font-mono)" }}>
              metal_nut (Official Split)
            </div>
          </div>

          <div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 4 }}>
              Active Model
            </div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
              PatchCore-v1
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
              WideResNet-50-2
            </div>
          </div>

          <div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 4 }}>
              Calibration Policy
            </div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
              3-Sigma Normal
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
              mean + 3σ (220 good train)
            </div>
          </div>

          <div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 4 }}>
              Process Threshold (τ)
            </div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "var(--accent-amber)", fontFamily: "var(--font-mono)" }}>
              {summary ? summary.threshold.toFixed(4) : "—"}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
              Score ≥ τ ⇒ DEFECT
            </div>
          </div>
        </div>
      </div>

      {analyticsLoading ? (
        <div style={{ padding: 60, textAlign: "center", color: "var(--text-muted)" }}>
          <RefreshCw size={24} className="animate-spin" style={{ margin: "0 auto 12px auto" }} />
          Computing deterministic inspection analytics from PostgreSQL persistence...
        </div>
      ) : !summary ? (
        <EmptyState
          icon="inspection"
          metadataTag="NO DATA"
          title="No Inspection Runs Available"
          description="Execute an evaluation run from the Visual Inspection Station or backend CLI to populate analytics."
        />
      ) : (
        <>
          {/* Section 3: KPI Ribbon */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(7, 1fr)",
              gap: 12,
              marginBottom: 20,
            }}
          >
            <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", padding: 14 }}>
              <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>Evaluated</div>
              <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-primary)", marginTop: 4 }}>
                {summary.total_images}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Official test split</div>
            </div>

            <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", padding: 14 }}>
              <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>PASS</div>
              <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-green)", marginTop: 4 }}>
                {summary.passed_count}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{((summary.passed_count / summary.total_images) * 100).toFixed(1)}% pass rate</div>
            </div>

            <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", padding: 14 }}>
              <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>DEFECT</div>
              <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-red)", marginTop: 4 }}>
                {summary.defect_count}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Flagged by model</div>
            </div>

            <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", padding: 14 }}>
              <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>Defect Rate</div>
              <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-amber)", marginTop: 4 }}>
                {(summary.observed_defect_rate * 100).toFixed(1)}%
              </div>
              <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Benchmark test-set</div>
            </div>

            <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", padding: 14 }}>
              <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>Image ROC-AUC</div>
              <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-cyan)", marginTop: 4 }}>
                {confusionMatrix?.image_roc_auc ? (confusionMatrix.image_roc_auc * 100).toFixed(1) + "%" : "—"}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Separation metric</div>
            </div>

            <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", padding: 14 }}>
              <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>F1-Score</div>
              <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-cyan)", marginTop: 4 }}>
                {confusionMatrix?.f1_score ? (confusionMatrix.f1_score * 100).toFixed(1) + "%" : "—"}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Harmonic balance</div>
            </div>

            <div style={{ backgroundColor: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-md)", padding: 14 }}>
              <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>Pixel ROC-AUC</div>
              <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "var(--font-mono)", color: "#10b981", marginTop: 4 }}>
                {localization?.pixel_roc_auc ? (localization.pixel_roc_auc * 100).toFixed(1) + "%" : "—"}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-muted)" }}>93 Defect Masks</div>
            </div>
          </div>

          {/* Section 4: Score Distribution Histogram */}
          {scoreDist && (
            <div
              style={{
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--border-default)",
                borderRadius: "var(--radius-md)",
                padding: 20,
                marginBottom: 20,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <BarChart2 size={16} color="var(--accent-cyan)" />
                    <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                      ANOMALY SCORE DISTRIBUTION & THRESHOLD ANALYSIS
                    </span>
                    <span
                      style={{
                        fontSize: 10,
                        fontFamily: "var(--font-mono)",
                        padding: "2px 6px",
                        borderRadius: 3,
                        backgroundColor: "rgba(16, 185, 129, 0.15)",
                        color: "var(--accent-green)",
                      }}
                    >
                      DERIVED ANALYTICS
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
                    Frequency distribution of Euclidean patch distances: Normal reference distribution vs Defective test distribution.
                  </div>
                </div>

                {/* Explanatory Legend */}
                <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: 12 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <div style={{ width: 12, height: 12, backgroundColor: "var(--accent-green)", borderRadius: 2 }} />
                    <span style={{ color: "var(--text-secondary)" }}>Normal Test (22 imgs)</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <div style={{ width: 12, height: 12, backgroundColor: "var(--accent-red)", borderRadius: 2 }} />
                    <span style={{ color: "var(--text-secondary)" }}>Defective Test (93 imgs)</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <div style={{ width: 14, height: 2, backgroundColor: "var(--accent-amber)" }} />
                    <span style={{ color: "var(--accent-amber)", fontWeight: 600, fontFamily: "var(--font-mono)" }}>
                      Threshold τ = {scoreDist.threshold.toFixed(4)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Histogram Visualization */}
              <div style={{ padding: "16px 0 10px 0" }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "flex-end",
                    gap: 6,
                    height: 160,
                    borderBottom: "1px solid var(--border-default)",
                    position: "relative",
                  }}
                >
                  {/* Threshold Line Overlay */}
                  {(() => {
                    const minS = scoreDist.overall_stats.min || 2.0;
                    const maxS = scoreDist.overall_stats.max || 4.5;
                    const pct = Math.max(0, Math.min(100, ((scoreDist.threshold - minS) / (maxS - minS)) * 100));
                    return (
                      <div
                        style={{
                          position: "absolute",
                          left: `${pct}%`,
                          top: 0,
                          bottom: 0,
                          width: 2,
                          backgroundColor: "var(--accent-amber)",
                          zIndex: 5,
                          boxShadow: "0 0 6px var(--accent-amber)",
                        }}
                      >
                        <div
                          style={{
                            position: "absolute",
                            top: -20,
                            left: -24,
                            fontSize: 10,
                            fontFamily: "var(--font-mono)",
                            color: "var(--accent-amber)",
                            backgroundColor: "rgba(0, 0, 0, 0.75)",
                            padding: "1px 4px",
                            borderRadius: 2,
                            whiteSpace: "nowrap",
                          }}
                        >
                          τ = {scoreDist.threshold.toFixed(2)}
                        </div>
                      </div>
                    );
                  })()}

                  {/* Histogram Bars */}
                  {scoreDist.histogram.map((bin, idx) => {
                    const maxBinTotal = Math.max(...scoreDist.histogram.map((b) => b.total_count), 1);
                    const normalHeightPct = (bin.normal_count / maxBinTotal) * 100;
                    const defectHeightPct = (bin.defect_count / maxBinTotal) * 100;

                    return (
                      <div
                        key={idx}
                        style={{
                          flex: 1,
                          display: "flex",
                          flexDirection: "column",
                          justifyContent: "flex-end",
                          height: "100%",
                          position: "relative",
                        }}
                        title={`Bin [${bin.bin_start.toFixed(2)} - ${bin.bin_end.toFixed(2)}]: Normal=${bin.normal_count}, Defect=${bin.defect_count}`}
                      >
                        {/* Defect Bar (top) */}
                        {bin.defect_count > 0 && (
                          <div
                            style={{
                              width: "100%",
                              height: `${defectHeightPct}%`,
                              backgroundColor: "rgba(239, 68, 68, 0.8)",
                              borderTopLeftRadius: 2,
                              borderTopRightRadius: 2,
                              transition: "height 0.3s ease",
                            }}
                          />
                        )}
                        {/* Normal Bar (bottom) */}
                        {bin.normal_count > 0 && (
                          <div
                            style={{
                              width: "100%",
                              height: `${normalHeightPct}%`,
                              backgroundColor: "rgba(16, 185, 129, 0.8)",
                              borderTopLeftRadius: bin.defect_count === 0 ? 2 : 0,
                              borderTopRightRadius: bin.defect_count === 0 ? 2 : 0,
                              transition: "height 0.3s ease",
                            }}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* X-Axis Range */}
                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                  <span>Min: {scoreDist.overall_stats.min?.toFixed(2)}</span>
                  <span>Median: {scoreDist.overall_stats.median?.toFixed(2)}</span>
                  <span>Max: {scoreDist.overall_stats.max?.toFixed(2)}</span>
                </div>
              </div>

              {/* Statistical Percentiles Grid */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr",
                  gap: 12,
                  marginTop: 14,
                  backgroundColor: "var(--bg-app)",
                  borderRadius: "var(--radius-sm)",
                  padding: 12,
                }}
              >
                <div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>Normal Distribution (Test)</div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4, fontFamily: "var(--font-mono)" }}>
                    Mean: <strong style={{ color: "var(--accent-green)" }}>{scoreDist.normal_stats.mean?.toFixed(4)}</strong> | Std: {scoreDist.normal_stats.std?.toFixed(4)}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2, fontFamily: "var(--font-mono)" }}>
                    Min: {scoreDist.normal_stats.min?.toFixed(2)} | P95: {scoreDist.normal_stats.p95?.toFixed(2)} | Max: {scoreDist.normal_stats.max?.toFixed(2)}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>Defective Distribution (Test)</div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4, fontFamily: "var(--font-mono)" }}>
                    Mean: <strong style={{ color: "var(--accent-red)" }}>{scoreDist.defective_stats.mean?.toFixed(4)}</strong> | Std: {scoreDist.defective_stats.std?.toFixed(4)}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2, fontFamily: "var(--font-mono)" }}>
                    Min: {scoreDist.defective_stats.min?.toFixed(2)} | P95: {scoreDist.defective_stats.p95?.toFixed(2)} | Max: {scoreDist.defective_stats.max?.toFixed(2)}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase" }}>Separation Margin (Delta)</div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4, fontFamily: "var(--font-mono)" }}>
                    Delta: <strong style={{ color: "var(--accent-cyan)" }}>+{(scoreDist.defective_stats.mean - scoreDist.normal_stats.mean).toFixed(4)}</strong>
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                    Clear inter-distribution gap verifying PatchCore feature selectivity.
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Section 5 & 6: Defect Category Analysis & Confusion Matrix */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1.3fr 1fr",
              gap: 16,
              marginBottom: 20,
            }}
          >
            {/* Defect Category Performance Table */}
            {defectAnalytics && (
              <div
                style={{
                  backgroundColor: "var(--bg-surface)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-md)",
                  padding: 18,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <Layers size={16} color="var(--accent-cyan)" />
                    <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                      DEFECT CATEGORY DETECTION PERFORMANCE
                    </span>
                  </div>
                  <span style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase" }}>
                    MVTec AD Benchmark
                  </span>
                </div>

                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border-default)", textAlign: "left", color: "var(--text-muted)" }}>
                      <th style={{ padding: "6px 8px" }}>CLASS</th>
                      <th style={{ padding: "6px 8px" }}>IMAGES</th>
                      <th style={{ padding: "6px 8px" }}>DETECTED</th>
                      <th style={{ padding: "6px 8px" }}>MISSED</th>
                      <th style={{ padding: "6px 8px" }}>ACCURACY</th>
                      <th style={{ padding: "6px 8px" }}>MEAN SCORE</th>
                    </tr>
                  </thead>
                  <tbody>
                    {defectAnalytics.classes.map((cls) => {
                      const isGood = cls.defect_class === "good";
                      return (
                        <tr key={cls.defect_class} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                          <td style={{ padding: "8px", fontWeight: 600, color: "var(--text-primary)", textTransform: "uppercase", fontFamily: "var(--font-mono)" }}>
                            {cls.defect_class}
                          </td>
                          <td style={{ padding: "8px", fontFamily: "var(--font-mono)" }}>{cls.image_count}</td>
                          <td style={{ padding: "8px", fontFamily: "var(--font-mono)", color: isGood ? "var(--accent-green)" : "var(--accent-red)", fontWeight: 600 }}>
                            {cls.detected_count}
                          </td>
                          <td style={{ padding: "8px", fontFamily: "var(--font-mono)", color: cls.missed_count > 0 ? "var(--accent-amber)" : "var(--text-muted)" }}>
                            {cls.missed_count}
                          </td>
                          <td style={{ padding: "8px", fontFamily: "var(--font-mono)", fontWeight: 600, color: cls.observed_detection_rate >= 0.95 ? "var(--accent-green)" : "var(--accent-amber)" }}>
                            {(cls.observed_detection_rate * 100).toFixed(1)}%
                          </td>
                          <td style={{ padding: "8px", fontFamily: "var(--font-mono)" }}>{cls.mean_score.toFixed(4)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Confusion Matrix & Classification Breakdown */}
            {confusionMatrix && (
              <div
                style={{
                  backgroundColor: "var(--bg-surface)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-md)",
                  padding: 18,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <Sliders size={16} color="var(--accent-cyan)" />
                    <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                      CONFUSION MATRIX & METRICS
                    </span>
                  </div>
                  <span style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--accent-amber)" }}>
                    τ = {confusionMatrix.threshold.toFixed(4)}
                  </span>
                </div>

                {/* 2x2 Grid */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 14 }}>
                  <div style={{ padding: 10, backgroundColor: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)", borderRadius: "var(--radius-xs)" }}>
                    <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase" }}>True Negative (TN)</div>
                    <div style={{ fontSize: 20, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-green)" }}>
                      {confusionMatrix.true_negatives}
                    </div>
                    <div style={{ fontSize: 10, color: "var(--text-muted)" }}>Normal passed correctly</div>
                  </div>

                  <div style={{ padding: 10, backgroundColor: "rgba(239, 68, 68, 0.08)", border: "1px solid rgba(239, 68, 68, 0.25)", borderRadius: "var(--radius-xs)" }}>
                    <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase" }}>False Positive (FP)</div>
                    <div style={{ fontSize: 20, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-amber)" }}>
                      {confusionMatrix.false_positives}
                    </div>
                    <div style={{ fontSize: 10, color: "var(--text-muted)" }}>False alarm (normal flagged)</div>
                  </div>

                  <div style={{ padding: 10, backgroundColor: "rgba(239, 68, 68, 0.08)", border: "1px solid rgba(239, 68, 68, 0.25)", borderRadius: "var(--radius-xs)" }}>
                    <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase" }}>False Negative (FN)</div>
                    <div style={{ fontSize: 20, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-red)" }}>
                      {confusionMatrix.false_negatives}
                    </div>
                    <div style={{ fontSize: 10, color: "var(--text-muted)" }}>Missed defect (score &lt; τ)</div>
                  </div>

                  <div style={{ padding: 10, backgroundColor: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)", borderRadius: "var(--radius-xs)" }}>
                    <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase" }}>True Positive (TP)</div>
                    <div style={{ fontSize: 20, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-green)" }}>
                      {confusionMatrix.true_positives}
                    </div>
                    <div style={{ fontSize: 10, color: "var(--text-muted)" }}>Defect caught correctly</div>
                  </div>
                </div>

                {/* Metrics Readout */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, fontSize: 11, fontFamily: "var(--font-mono)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 8px", backgroundColor: "var(--bg-app)", borderRadius: 3 }}>
                    <span style={{ color: "var(--text-muted)" }}>Precision:</span>
                    <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{(confusionMatrix.precision * 100).toFixed(1)}%</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 8px", backgroundColor: "var(--bg-app)", borderRadius: 3 }}>
                    <span style={{ color: "var(--text-muted)" }}>Recall (Sens):</span>
                    <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{(confusionMatrix.recall * 100).toFixed(1)}%</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 8px", backgroundColor: "var(--bg-app)", borderRadius: 3 }}>
                    <span style={{ color: "var(--text-muted)" }}>Specificity:</span>
                    <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{(confusionMatrix.specificity * 100).toFixed(1)}%</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 8px", backgroundColor: "var(--bg-app)", borderRadius: 3 }}>
                    <span style={{ color: "var(--text-muted)" }}>F1-Score:</span>
                    <span style={{ fontWeight: 600, color: "var(--accent-cyan)" }}>{(confusionMatrix.f1_score * 100).toFixed(1)}%</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Section 8 & 9: Localization Analytics & Provenance Panel */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 16,
              marginBottom: 20,
            }}
          >
            {/* Localization Analytics */}
            {localization && (
              <div
                style={{
                  backgroundColor: "var(--bg-surface)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-md)",
                  padding: 18,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                  <Eye size={16} color="var(--accent-cyan)" />
                  <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                    PIXEL-LEVEL DEFECT LOCALIZATION PERFORMANCE
                  </span>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 10px", backgroundColor: "var(--bg-app)", borderRadius: "var(--radius-xs)" }}>
                    <span style={{ color: "var(--text-muted)" }}>Pixel ROC-AUC</span>
                    <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: "#10b981", fontSize: 14 }}>
                      {localization.pixel_roc_auc ? (localization.pixel_roc_auc * 100).toFixed(2) + "%" : "—"}
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 10px", backgroundColor: "var(--bg-app)", borderRadius: "var(--radius-xs)" }}>
                    <span style={{ color: "var(--text-muted)" }}>Ground Truth Masks Evaluated</span>
                    <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>{localization.mask_evaluated_images} Masks</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 10px", backgroundColor: "var(--bg-app)", borderRadius: "var(--radius-xs)" }}>
                    <span style={{ color: "var(--text-muted)" }}>Localization Method</span>
                    <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-secondary)", fontSize: 11 }}>{localization.localization_method}</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 10px", backgroundColor: "var(--bg-app)", borderRadius: "var(--radius-xs)" }}>
                    <span style={{ color: "var(--text-muted)" }}>Processed Grid Resolution</span>
                    <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>{localization.resolution}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Provenance Panel */}
            {provenance && (
              <div
                style={{
                  backgroundColor: "var(--bg-surface)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-md)",
                  padding: 18,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                  <Database size={16} color="var(--accent-cyan)" />
                  <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                    PIPELINE PROVENANCE & CALIBRATION LINEAGE
                  </span>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>Dataset Identifier</span>
                    <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>{provenance.dataset_identifier}</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>Model Identifier</span>
                    <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>{provenance.model_version}</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>Feature Config</span>
                    <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>{provenance.feature_config_version}</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>Decision Policy</span>
                    <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>{provenance.policy_version}</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>Normal Calibration Base</span>
                    <span style={{ fontFamily: "var(--font-mono)", color: "var(--accent-cyan)" }}>
                      220 train normal images (mean={String(provenance.normal_training_stats.normal_score_mean || "2.4895")}, std={String(provenance.normal_training_stats.normal_score_std || "0.1087")})
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ color: "var(--text-muted)" }}>Memory Bank Size</span>
                    <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>8,624 coreset patch vectors (seed=42)</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Section 6 (Model / Policy Comparison) */}
          <div
            style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-md)",
              padding: 18,
              marginBottom: 20,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <LineChart size={16} color="var(--accent-cyan)" />
                <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                  CROSS-MODEL & POLICY COMPARISON
                </span>
              </div>
              <span
                style={{
                  fontSize: 10,
                  fontFamily: "var(--font-mono)",
                  padding: "2px 6px",
                  borderRadius: 3,
                  backgroundColor: comparison?.is_available ? "rgba(16, 185, 129, 0.15)" : "rgba(245, 158, 11, 0.12)",
                  color: comparison?.is_available ? "var(--accent-green)" : "var(--accent-amber)",
                }}
              >
                {comparison?.is_available ? "ACTIVE COMPARISON" : "INSUFFICIENT COMPARISON RUNS"}
              </span>
            </div>

            {comparison && !comparison.is_available ? (
              <div
                style={{
                  padding: "16px 20px",
                  backgroundColor: "var(--bg-app)",
                  borderRadius: "var(--radius-sm)",
                  border: "1px dashed var(--border-default)",
                  fontSize: 12,
                  color: "var(--text-secondary)",
                  lineHeight: 1.5,
                }}
              >
                <strong>Comparative evaluation unavailable:</strong> {comparison.reason}
                <div style={{ marginTop: 6, fontSize: 11, color: "var(--text-muted)" }}>
                  In accordance with MachIntel Master Rule, hypothetical or fabricated comparison baselines are strictly forbidden. When subsequent model checkpoints or feature configurations are trained and evaluated, comparative metrics will populate automatically.
                </div>
              </div>
            ) : comparison?.runs && (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border-default)", textAlign: "left", color: "var(--text-muted)" }}>
                    <th style={{ padding: "6px 8px" }}>MODEL</th>
                    <th style={{ padding: "6px 8px" }}>POLICY</th>
                    <th style={{ padding: "6px 8px" }}>THRESHOLD</th>
                    <th style={{ padding: "6px 8px" }}>ROC-AUC</th>
                    <th style={{ padding: "6px 8px" }}>PR-AUC</th>
                    <th style={{ padding: "6px 8px" }}>F1</th>
                    <th style={{ padding: "6px 8px" }}>PIXEL ROC-AUC</th>
                    <th style={{ padding: "6px 8px" }}>TIMESTAMP</th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.runs.map((cr) => (
                    <tr key={cr.run_id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                      <td style={{ padding: "8px", fontFamily: "var(--font-mono)", fontWeight: 600 }}>{cr.model_version}</td>
                      <td style={{ padding: "8px", fontFamily: "var(--font-mono)" }}>{cr.policy_version}</td>
                      <td style={{ padding: "8px", fontFamily: "var(--font-mono)" }}>{cr.threshold.toFixed(4)}</td>
                      <td style={{ padding: "8px", fontFamily: "var(--font-mono)", color: "var(--accent-cyan)" }}>{cr.roc_auc ? (cr.roc_auc * 100).toFixed(1) + "%" : "—"}</td>
                      <td style={{ padding: "8px", fontFamily: "var(--font-mono)" }}>{cr.pr_auc ? (cr.pr_auc * 100).toFixed(1) + "%" : "—"}</td>
                      <td style={{ padding: "8px", fontFamily: "var(--font-mono)" }}>{cr.f1_score ? (cr.f1_score * 100).toFixed(1) + "%" : "—"}</td>
                      <td style={{ padding: "8px", fontFamily: "var(--font-mono)", color: "#10b981" }}>{cr.pixel_roc_auc ? (cr.pixel_roc_auc * 100).toFixed(1) + "%" : "—"}</td>
                      <td style={{ padding: "8px", color: "var(--text-muted)", fontSize: 11 }}>{new Date(cr.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Section 7: Run History */}
          <div
            style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-md)",
              padding: 18,
              marginBottom: 40,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Clock size={16} color="var(--accent-cyan)" />
                <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                  INSPECTION RUN AUDIT HISTORY
                </span>
              </div>
              <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                {runs.length} Runs Recorded in PostgreSQL
              </span>
            </div>

            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border-default)", textAlign: "left", color: "var(--text-muted)" }}>
                  <th style={{ padding: "6px 8px" }}>RUN ID</th>
                  <th style={{ padding: "6px 8px" }}>TIMESTAMP</th>
                  <th style={{ padding: "6px 8px" }}>DATASET</th>
                  <th style={{ padding: "6px 8px" }}>MODEL</th>
                  <th style={{ padding: "6px 8px" }}>POLICY</th>
                  <th style={{ padding: "6px 8px" }}>EVALUATED</th>
                  <th style={{ padding: "6px 8px" }}>PASS</th>
                  <th style={{ padding: "6px 8px" }}>DEFECT</th>
                  <th style={{ padding: "6px 8px" }}>THRESHOLD</th>
                  <th style={{ padding: "6px 8px" }}>STATUS</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => {
                  const isSelected = r.id === selectedRunId;
                  return (
                    <tr
                      key={r.id}
                      onClick={() => setSelectedRunId(r.id)}
                      style={{
                        borderBottom: "1px solid var(--border-subtle)",
                        backgroundColor: isSelected ? "rgba(6, 182, 212, 0.08)" : "transparent",
                        cursor: "pointer",
                      }}
                    >
                      <td style={{ padding: "8px", fontFamily: "var(--font-mono)", color: isSelected ? "var(--accent-cyan)" : "var(--text-primary)" }}>
                        {r.id.slice(0, 8)}...
                      </td>
                      <td style={{ padding: "8px", color: "var(--text-muted)" }}>
                        {new Date(r.created_at).toLocaleString()}
                      </td>
                      <td style={{ padding: "8px", fontFamily: "var(--font-mono)" }}>{r.dataset_identifier}</td>
                      <td style={{ padding: "8px", fontFamily: "var(--font-mono)" }}>{r.model_version}</td>
                      <td style={{ padding: "8px", fontFamily: "var(--font-mono)" }}>{r.policy_version}</td>
                      <td style={{ padding: "8px", fontFamily: "var(--font-mono)" }}>{r.total_images}</td>
                      <td style={{ padding: "8px", fontFamily: "var(--font-mono)", color: "var(--accent-green)" }}>{r.passed_count}</td>
                      <td style={{ padding: "8px", fontFamily: "var(--font-mono)", color: "var(--accent-red)" }}>{r.defect_count}</td>
                      <td style={{ padding: "8px", fontFamily: "var(--font-mono)" }}>{r.threshold.toFixed(4)}</td>
                      <td style={{ padding: "8px" }}>
                        <span
                          style={{
                            padding: "2px 6px",
                            borderRadius: 3,
                            fontSize: 10,
                            fontFamily: "var(--font-mono)",
                            backgroundColor: "rgba(16, 185, 129, 0.15)",
                            color: "var(--accent-green)",
                          }}
                        >
                          {r.status}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </AppShell>
  );
}
