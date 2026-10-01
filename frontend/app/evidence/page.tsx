"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/common/EmptyState";
import { apiClient } from "@/lib/api-client";
import {
  EvidenceBundle,
  EvidenceDomain,
  EvidenceProvenance,
  EvidenceQualityState,
  EvidenceRecord,
  EvidenceRelationship,
  EvidenceTimelineItem,
  EvidenceType,
} from "@/types/evidence";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  Eye,
  FileCheck,
  FileText,
  Filter,
  Flame,
  GitBranch,
  Layers,
  Link as LinkIcon,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  Sparkles,
  Tag,
  Zap,
} from "lucide-react";
import Link from "next/link";

export default function EvidencePage() {
  // Domain switch
  const [selectedDomain, setSelectedDomain] = useState<EvidenceDomain>("MACHINE_HEALTH");
  const [viewMode, setViewMode] = useState<"stream" | "bundles">("stream");

  // Filter states
  const [evidenceTypeFilter, setEvidenceTypeFilter] = useState<string>("ALL");
  const [qualityFilter, setQualityFilter] = useState<string>("ALL");
  const [searchEntityId, setSearchEntityId] = useState<string>("");

  // Data states
  const [records, setRecords] = useState<EvidenceRecord[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [bundles, setBundles] = useState<EvidenceBundle[]>([]);
  const [selectedRecord, setSelectedRecord] = useState<EvidenceRecord | null>(null);
  const [selectedBundle, setSelectedBundle] = useState<EvidenceBundle | null>(null);

  // Relationships & Provenance for selected record
  const [relationships, setRelationships] = useState<{
    outgoing: EvidenceRelationship[];
    incoming: EvidenceRelationship[];
  } | null>(null);
  const [provenance, setProvenance] = useState<EvidenceProvenance | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // 1. Fetch evidence records
  const fetchEvidence = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.searchEvidence({
        domain: selectedDomain,
        evidence_type: evidenceTypeFilter !== "ALL" ? evidenceTypeFilter : undefined,
        quality_state: qualityFilter !== "ALL" ? qualityFilter : undefined,
        entity_id: searchEntityId.trim() ? searchEntityId.trim() : undefined,
        limit: 100,
      });
      const recs = res?.records || [];
      setRecords(recs);
      setTotalCount(res?.total ?? 0);
      if (recs.length > 0 && !selectedRecord) {
        handleSelectRecord(recs[0]);
      }
    } catch (err: unknown) {
      console.error("Failed to load evidence records:", err);
      setError(err instanceof Error ? err.message : "Failed to load evidence records.");
    } finally {
      setLoading(false);
    }
  };

  // 2. Fetch evidence bundles
  const fetchBundles = async () => {
    try {
      const res = await apiClient.getEvidenceBundles({
        domain: selectedDomain,
        limit: 50,
      });
      setBundles(res);
      if (res.length > 0 && !selectedBundle) {
        setSelectedBundle(res[0]);
      }
    } catch (err: unknown) {
      console.error("Failed to load evidence bundles:", err);
    }
  };

  useEffect(() => {
    fetchEvidence();
    fetchBundles();
  }, [selectedDomain, evidenceTypeFilter, qualityFilter]);

  // 3. Handle selecting an evidence record
  const handleSelectRecord = async (rec: EvidenceRecord) => {
    setSelectedRecord(rec);
    try {
      setDetailLoading(true);
      const [rels, prov] = await Promise.all([
        apiClient.getEvidenceRelationships(rec.id).catch(() => null),
        apiClient.getEvidenceProvenance(rec.id).catch(() => null),
      ]);
      setRelationships(rels);
      setProvenance(prov);
    } catch (err) {
      console.error("Failed to load relationships or provenance:", err);
    } finally {
      setDetailLoading(false);
    }
  };

  const getQualityBadge = (state: EvidenceQualityState) => {
    switch (state) {
      case "VERIFIED":
        return { bg: "rgba(16, 185, 129, 0.15)", text: "#10b981", border: "rgba(16, 185, 129, 0.3)" };
      case "DERIVED":
        return { bg: "rgba(6, 182, 212, 0.15)", text: "var(--accent-cyan)", border: "rgba(6, 182, 212, 0.3)" };
      case "BENCHMARK_GROUND_TRUTH":
        return { bg: "rgba(139, 92, 246, 0.15)", text: "#a78bfa", border: "rgba(139, 92, 246, 0.3)" };
      case "PROVENANCE_ONLY":
        return { bg: "rgba(245, 158, 11, 0.15)", text: "var(--accent-amber)", border: "rgba(245, 158, 11, 0.3)" };
      default:
        return { bg: "rgba(148, 163, 184, 0.1)", text: "var(--text-muted)", border: "var(--border-default)" };
    }
  };

  const getEvidenceTypeColor = (type: EvidenceType) => {
    switch (type) {
      case "TELEMETRY":
      case "IMAGE":
        return "var(--accent-green)";
      case "RUL_PREDICTION":
      case "ANOMALY_SCORE":
        return "var(--accent-cyan)";
      case "HEALTH_INDEX":
      case "INSPECTION_DECISION":
        return "var(--accent-amber)";
      case "RISK_ASSESSMENT":
      case "ALERT":
        return "var(--accent-red)";
      case "GROUND_TRUTH":
        return "#a78bfa";
      case "LOCALIZATION":
        return "#34d399";
      default:
        return "var(--text-secondary)";
    }
  };

  return (
    <AppShell>
      <PageHeader
        title="Evidence Intelligence"
        subtitle="Unified multi-domain evidence abstraction, causal lineage tracing, and strictly segregated asset proofs."
        breadcrumbs={[{ label: "Intelligence" }, { label: "Evidence Intelligence" }]}
        actions={
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => {
                fetchEvidence();
                fetchBundles();
              }}
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
          padding: "12px 16px",
          backgroundColor: "rgba(6, 182, 212, 0.05)",
          border: "1px solid rgba(6, 182, 212, 0.25)",
          borderRadius: "var(--radius-sm)",
          fontSize: 12,
          color: "var(--text-secondary)",
          marginBottom: 20,
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        <span
          style={{
            fontSize: 10,
            fontWeight: 700,
            fontFamily: "var(--font-mono)",
            padding: "3px 8px",
            borderRadius: 3,
            backgroundColor: "rgba(6, 182, 212, 0.2)",
            color: "var(--accent-cyan)",
            whiteSpace: "nowrap",
          }}
        >
          DOMAIN ISOLATION ENFORCED
        </span>
        <span style={{ lineHeight: 1.5 }}>
          Machine Health (NASA C-MAPSS) and Visual Inspection (MVTec AD) evidence records are strictly segregated. Cross-domain relationships are rejected by policy to prevent unsupported multimodal fusion.
        </span>
      </div>

      {/* Controls Strip: Domain Selector, View Switcher, and Filters */}
      <div
        style={{
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border-default)",
          borderRadius: "var(--radius-md)",
          padding: 16,
          marginBottom: 20,
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 16,
        }}
      >
        {/* Domain Tabs */}
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginRight: 6 }}>
            Domain:
          </span>
          <button
            onClick={() => {
              setSelectedDomain("MACHINE_HEALTH");
              setSelectedRecord(null);
            }}
            style={{
              padding: "7px 14px",
              borderRadius: "var(--radius-sm)",
              fontSize: 12,
              fontWeight: 600,
              fontFamily: "var(--font-mono)",
              display: "flex",
              alignItems: "center",
              gap: 8,
              cursor: "pointer",
              backgroundColor: selectedDomain === "MACHINE_HEALTH" ? "rgba(6, 182, 212, 0.15)" : "var(--bg-app)",
              color: selectedDomain === "MACHINE_HEALTH" ? "var(--accent-cyan)" : "var(--text-secondary)",
              border: `1px solid ${selectedDomain === "MACHINE_HEALTH" ? "var(--accent-cyan)" : "var(--border-default)"}`,
              transition: "all 0.15s ease",
            }}
          >
            <Cpu size={14} /> MACHINE HEALTH (C-MAPSS)
          </button>
          <button
            onClick={() => {
              setSelectedDomain("VISUAL_INSPECTION");
              setSelectedRecord(null);
            }}
            style={{
              padding: "7px 14px",
              borderRadius: "var(--radius-sm)",
              fontSize: 12,
              fontWeight: 600,
              fontFamily: "var(--font-mono)",
              display: "flex",
              alignItems: "center",
              gap: 8,
              cursor: "pointer",
              backgroundColor: selectedDomain === "VISUAL_INSPECTION" ? "rgba(6, 182, 212, 0.15)" : "var(--bg-app)",
              color: selectedDomain === "VISUAL_INSPECTION" ? "var(--accent-cyan)" : "var(--text-secondary)",
              border: `1px solid ${selectedDomain === "VISUAL_INSPECTION" ? "var(--accent-cyan)" : "var(--border-default)"}`,
              transition: "all 0.15s ease",
            }}
          >
            <Eye size={14} /> VISUAL INSPECTION (MVTec)
          </button>
        </div>

        {/* View Mode Switcher */}
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <button
            onClick={() => setViewMode("stream")}
            style={{
              padding: "6px 12px",
              borderRadius: "var(--radius-xs)",
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
              backgroundColor: viewMode === "stream" ? "var(--bg-card)" : "transparent",
              color: viewMode === "stream" ? "var(--text-primary)" : "var(--text-muted)",
              border: `1px solid ${viewMode === "stream" ? "var(--border-default)" : "transparent"}`,
            }}
          >
            Evidence Stream ({totalCount})
          </button>
          <button
            onClick={() => setViewMode("bundles")}
            style={{
              padding: "6px 12px",
              borderRadius: "var(--radius-xs)",
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
              backgroundColor: viewMode === "bundles" ? "var(--bg-card)" : "transparent",
              color: viewMode === "bundles" ? "var(--text-primary)" : "var(--text-muted)",
              border: `1px solid ${viewMode === "bundles" ? "var(--border-default)" : "transparent"}`,
            }}
          >
            Evidence Bundles ({bundles.length})
          </button>
        </div>

        {/* Filters */}
        <div style={{ display: "flex", gap: 10, alignItems: "center", width: "100%", borderTop: "1px solid var(--border-subtle)", paddingTop: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Type:</span>
            <select
              value={evidenceTypeFilter}
              onChange={(e) => setEvidenceTypeFilter(e.target.value)}
              style={{
                backgroundColor: "var(--bg-app)",
                border: "1px solid var(--border-default)",
                color: "var(--text-primary)",
                borderRadius: "var(--radius-xs)",
                padding: "4px 8px",
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                outline: "none",
              }}
            >
              <option value="ALL">ALL TYPES</option>
              {selectedDomain === "MACHINE_HEALTH" ? (
                <>
                  <option value="TELEMETRY">TELEMETRY</option>
                  <option value="FEATURE">FEATURE</option>
                  <option value="RUL_PREDICTION">RUL_PREDICTION</option>
                  <option value="HEALTH_INDEX">HEALTH_INDEX</option>
                  <option value="RISK_ASSESSMENT">RISK_ASSESSMENT</option>
                  <option value="ALERT">ALERT</option>
                </>
              ) : (
                <>
                  <option value="DATASET_PROVENANCE">DATASET_PROVENANCE</option>
                  <option value="INSPECTION_DECISION">INSPECTION_DECISION</option>
                  <option value="ANOMALY_SCORE">ANOMALY_SCORE</option>
                  <option value="LOCALIZATION">LOCALIZATION</option>
                  <option value="GROUND_TRUTH">GROUND_TRUTH</option>
                  <option value="ANALYTICS">ANALYTICS</option>
                </>
              )}
            </select>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Quality State:</span>
            <select
              value={qualityFilter}
              onChange={(e) => setQualityFilter(e.target.value)}
              style={{
                backgroundColor: "var(--bg-app)",
                border: "1px solid var(--border-default)",
                color: "var(--text-primary)",
                borderRadius: "var(--radius-xs)",
                padding: "4px 8px",
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                outline: "none",
              }}
            >
              <option value="ALL">ALL STATES</option>
              <option value="VERIFIED">VERIFIED</option>
              <option value="DERIVED">DERIVED</option>
              <option value="BENCHMARK_GROUND_TRUTH">BENCHMARK_GROUND_TRUTH</option>
              <option value="PROVENANCE_ONLY">PROVENANCE_ONLY</option>
            </select>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 6, flex: 1, justifyContent: "flex-end" }}>
            <div style={{ position: "relative", width: 220 }}>
              <Search size={13} style={{ position: "absolute", left: 8, top: 8, color: "var(--text-muted)" }} />
              <input
                type="text"
                placeholder="Filter by Entity ID..."
                value={searchEntityId}
                onChange={(e) => setSearchEntityId(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && fetchEvidence()}
                style={{
                  width: "100%",
                  backgroundColor: "var(--bg-app)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-xs)",
                  padding: "5px 8px 5px 26px",
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  color: "var(--text-primary)",
                  outline: "none",
                }}
              />
            </div>
            <button
              onClick={fetchEvidence}
              className="btn btn-secondary"
              style={{ fontSize: 11, padding: "5px 10px" }}
            >
              Filter
            </button>
          </div>
        </div>
      </div>

      {/* Main Workspace Layout: 2-column or Bundles View */}
      {viewMode === "stream" ? (
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 16 }}>
          {/* Left Column: Evidence List */}
          <div
            style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-md)",
              padding: 16,
              height: "75vh",
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: 10,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
              <span style={{ fontSize: 12, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>
                PERSISTED EVIDENCE RECORDS ({records?.length ?? 0})
              </span>
              <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                Sorted by {selectedDomain === "MACHINE_HEALTH" ? "Observation Cycle" : "Timestamp"}
              </span>
            </div>

            {loading ? (
              <div style={{ padding: 40, textAlign: "center", color: "var(--text-muted)" }}>
                <RefreshCw size={20} className="animate-spin" style={{ margin: "0 auto 8px auto" }} />
                Loading authoritative evidence records...
              </div>
            ) : records.length === 0 ? (
              <EmptyState
                icon="terminal"
                metadataTag="NO EVIDENCE"
                title="No Evidence Records Found"
                description="No persisted records match the selected domain and filter criteria."
              />
            ) : (
              records.map((rec) => {
                const isSelected = selectedRecord?.id === rec.id;
                const qb = getQualityBadge(rec.quality_state);
                const typeColor = getEvidenceTypeColor(rec.evidence_type);

                return (
                  <div
                    key={rec.id}
                    onClick={() => handleSelectRecord(rec)}
                    style={{
                      padding: 12,
                      backgroundColor: isSelected ? "rgba(6, 182, 212, 0.08)" : "var(--bg-app)",
                      border: `1px solid ${isSelected ? "var(--accent-cyan)" : "var(--border-subtle)"}`,
                      borderRadius: "var(--radius-sm)",
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span
                          style={{
                            fontSize: 10,
                            fontFamily: "var(--font-mono)",
                            fontWeight: 700,
                            color: typeColor,
                            padding: "2px 6px",
                            backgroundColor: "rgba(255, 255, 255, 0.03)",
                            borderRadius: 3,
                            border: `1px solid ${typeColor}40`,
                          }}
                        >
                          {rec.evidence_type}
                        </span>
                        <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                          {rec.source}
                        </span>
                      </div>
                      <span
                        style={{
                          fontSize: 9,
                          fontFamily: "var(--font-mono)",
                          padding: "2px 6px",
                          borderRadius: 3,
                          backgroundColor: qb.bg,
                          color: qb.text,
                          border: `1px solid ${qb.border}`,
                        }}
                      >
                        {rec.quality_state}
                      </span>
                    </div>

                    <div style={{ fontSize: 12, color: "var(--text-primary)", marginBottom: 8, lineHeight: 1.4 }}>
                      {rec.explanation || "No explanation provided for this evidence record."}
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                      <span>
                        Entity: <code style={{ color: "var(--accent-cyan)" }}>{rec.entity_type}:{rec.entity_id.slice(0, 8)}...</code>
                      </span>
                      {rec.observation_cycle !== null && rec.observation_cycle !== undefined ? (
                        <span style={{ color: "var(--accent-amber)" }}>Cycle: {rec.observation_cycle}</span>
                      ) : rec.observation_time ? (
                        <span>{new Date(rec.observation_time).toLocaleTimeString()}</span>
                      ) : (
                        <span>Cycle/Time: NULL</span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Right Column: Evidence Detail & Lineage Drawer */}
          <div
            style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-md)",
              padding: 18,
              height: "75vh",
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: 16,
            }}
          >
            {selectedRecord ? (
              <>
                {/* Header */}
                <div style={{ borderBottom: "1px solid var(--border-subtle)", paddingBottom: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <span style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                      EVIDENCE ID: {selectedRecord.id}
                    </span>
                    <span
                      style={{
                        fontSize: 9,
                        fontFamily: "var(--font-mono)",
                        padding: "2px 6px",
                        borderRadius: 3,
                        ...getQualityBadge(selectedRecord.quality_state),
                      }}
                    >
                      {selectedRecord.quality_state}
                    </span>
                  </div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                    {selectedRecord.evidence_type}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>
                    {selectedRecord.explanation}
                  </div>
                </div>

                {/* Structured Payload Values */}
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 8, letterSpacing: "0.05em" }}>
                    Structured Payload
                  </div>
                  <div
                    style={{
                      backgroundColor: "var(--bg-app)",
                      borderRadius: "var(--radius-sm)",
                      padding: 12,
                      fontFamily: "var(--font-mono)",
                      fontSize: 11,
                      color: "var(--text-primary)",
                      border: "1px solid var(--border-subtle)",
                      overflowX: "auto",
                    }}
                  >
                    {selectedRecord.value ? (
                      <pre style={{ margin: 0 }}>{JSON.stringify(selectedRecord.value, null, 2)}</pre>
                    ) : (
                      <span style={{ color: "var(--text-muted)" }}>No structured payload value</span>
                    )}
                  </div>
                </div>

                {/* Metadata & Lineage Spec */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, fontSize: 11 }}>
                  <div style={{ padding: 10, backgroundColor: "var(--bg-app)", borderRadius: "var(--radius-xs)" }}>
                    <div style={{ color: "var(--text-muted)", marginBottom: 2 }}>Domain</div>
                    <div style={{ fontFamily: "var(--font-mono)", color: "var(--accent-cyan)", fontWeight: 600 }}>{selectedRecord.domain}</div>
                  </div>
                  <div style={{ padding: 10, backgroundColor: "var(--bg-app)", borderRadius: "var(--radius-xs)" }}>
                    <div style={{ color: "var(--text-muted)", marginBottom: 2 }}>Source Reference</div>
                    <div style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {selectedRecord.source_reference}
                    </div>
                  </div>
                  <div style={{ padding: 10, backgroundColor: "var(--bg-app)", borderRadius: "var(--radius-xs)" }}>
                    <div style={{ color: "var(--text-muted)", marginBottom: 2 }}>Observation Cycle</div>
                    <div style={{ fontFamily: "var(--font-mono)", color: "var(--accent-amber)" }}>
                      {selectedRecord.observation_cycle !== null && selectedRecord.observation_cycle !== undefined ? selectedRecord.observation_cycle : "N/A (Optical/Static)"}
                    </div>
                  </div>
                  <div style={{ padding: 10, backgroundColor: "var(--bg-app)", borderRadius: "var(--radius-xs)" }}>
                    <div style={{ color: "var(--text-muted)", marginBottom: 2 }}>Calibrated Confidence</div>
                    <div style={{ fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                      {selectedRecord.confidence !== null ? selectedRecord.confidence : "NULL (Omitted per policy)"}
                    </div>
                  </div>
                </div>

                {/* Causal Lineage & Relationships */}
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 8, letterSpacing: "0.05em", display: "flex", alignItems: "center", gap: 6 }}>
                    <GitBranch size={13} color="var(--accent-cyan)" />
                    Causal Graph Relationships
                  </div>

                  {detailLoading ? (
                    <div style={{ fontSize: 11, color: "var(--text-muted)", padding: 10 }}>Loading graph edges...</div>
                  ) : relationships && (relationships.outgoing.length > 0 || relationships.incoming.length > 0) ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                      {relationships.outgoing.map((rel) => (
                        <div
                          key={rel.id}
                          style={{
                            padding: "8px 10px",
                            backgroundColor: "var(--bg-app)",
                            borderRadius: "var(--radius-xs)",
                            borderLeft: "3px solid var(--accent-cyan)",
                            fontSize: 11,
                            fontFamily: "var(--font-mono)",
                          }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)", marginBottom: 2 }}>
                            <span style={{ color: "var(--accent-cyan)", fontWeight: 700 }}>{rel.relationship_type}</span>
                            <span>Target: {rel.target_evidence_id.slice(0, 8)}...</span>
                          </div>
                          <div style={{ color: "var(--text-secondary)", fontSize: 10 }}>
                            {rel.target_evidence?.explanation || `Linked evidence: ${rel.target_evidence_id}`}
                          </div>
                        </div>
                      ))}

                      {relationships.incoming.map((rel) => (
                        <div
                          key={rel.id}
                          style={{
                            padding: "8px 10px",
                            backgroundColor: "var(--bg-app)",
                            borderRadius: "var(--radius-xs)",
                            borderLeft: "3px solid var(--accent-amber)",
                            fontSize: 11,
                            fontFamily: "var(--font-mono)",
                          }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)", marginBottom: 2 }}>
                            <span style={{ color: "var(--accent-amber)", fontWeight: 700 }}>INCOMING: {rel.relationship_type}</span>
                            <span>Source: {rel.source_evidence_id.slice(0, 8)}...</span>
                          </div>
                          <div style={{ color: "var(--text-secondary)", fontSize: 10 }}>
                            {rel.source_evidence?.explanation || `Source evidence: ${rel.source_evidence_id}`}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ fontSize: 11, color: "var(--text-muted)", padding: 8, backgroundColor: "var(--bg-app)", borderRadius: "var(--radius-xs)" }}>
                      No direct graph relationships registered for this root evidence node.
                    </div>
                  )}
                </div>

                {/* Provenance Block */}
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 8, letterSpacing: "0.05em", display: "flex", alignItems: "center", gap: 6 }}>
                    <Database size={13} color="var(--accent-cyan)" />
                    Provenance & Calibration Lineage
                  </div>
                  <div
                    style={{
                      padding: 10,
                      backgroundColor: "var(--bg-app)",
                      borderRadius: "var(--radius-xs)",
                      fontSize: 11,
                      fontFamily: "var(--font-mono)",
                      color: "var(--text-secondary)",
                      border: "1px solid var(--border-subtle)",
                    }}
                  >
                    <div>Model Version: <span style={{ color: "var(--text-primary)" }}>{selectedRecord.model_version || "N/A"}</span></div>
                    <div>Feature Version: <span style={{ color: "var(--text-primary)" }}>{selectedRecord.feature_version || "N/A"}</span></div>
                    <div>Policy Version: <span style={{ color: "var(--text-primary)" }}>{selectedRecord.policy_version || "N/A"}</span></div>
                    <div style={{ marginTop: 6, paddingTop: 6, borderTop: "1px dashed var(--border-subtle)", fontSize: 10 }}>
                      <pre style={{ margin: 0, color: "var(--text-muted)" }}>
                        {JSON.stringify(selectedRecord.provenance, null, 2)}
                      </pre>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div style={{ padding: 40, textAlign: "center", color: "var(--text-muted)" }}>
                Select an evidence record from the list to view its forensic properties, causal lineage, and provenance.
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Bundles Browser */
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1.5fr", gap: 16 }}>
          {/* Bundle List */}
          <div
            style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-md)",
              padding: 16,
              height: "75vh",
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: 10,
            }}
          >
            <div style={{ fontSize: 12, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-primary)", marginBottom: 6 }}>
              ASSEMBLED EVIDENCE BUNDLES ({bundles.length})
            </div>

            {bundles.length === 0 ? (
              <EmptyState
                icon="terminal"
                metadataTag="NO BUNDLES"
                title="No Bundles Assembled"
                description="No evidence bundles match the selected domain."
              />
            ) : (
              bundles.map((b) => {
                const isSelected = selectedBundle?.id === b.id;
                return (
                  <div
                    key={b.id}
                    onClick={() => setSelectedBundle(b)}
                    style={{
                      padding: 12,
                      backgroundColor: isSelected ? "rgba(6, 182, 212, 0.08)" : "var(--bg-app)",
                      border: `1px solid ${isSelected ? "var(--accent-cyan)" : "var(--border-subtle)"}`,
                      borderRadius: "var(--radius-sm)",
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                      <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
                        {b.bundle_name}
                      </span>
                      <span
                        style={{
                          fontSize: 10,
                          fontFamily: "var(--font-mono)",
                          padding: "2px 6px",
                          borderRadius: 3,
                          backgroundColor: "rgba(6, 182, 212, 0.15)",
                          color: "var(--accent-cyan)",
                        }}
                      >
                        {b.items?.length ?? 0} Proofs
                      </span>
                    </div>
                    <div style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.4, marginBottom: 6 }}>
                      {b.description}
                    </div>
                    <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                      Entity: {b.entity_type}:{b.entity_id ? b.entity_id.slice(0, 16) : "—"} | Assembled: {new Date(b.created_at).toLocaleDateString()}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Bundle Item Inspector */}
          <div
            style={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-md)",
              padding: 18,
              height: "75vh",
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: 14,
            }}
          >
            {selectedBundle ? (
              <>
                <div style={{ borderBottom: "1px solid var(--border-subtle)", paddingBottom: 12 }}>
                  <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--accent-cyan)" }}>
                    EVIDENCE BUNDLE CONTEXT
                  </div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", fontFamily: "var(--font-mono)", marginTop: 2 }}>
                    {selectedBundle.bundle_name}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>
                    {selectedBundle.description}
                  </div>
                </div>

                <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Ordered Proof Sequence ({selectedBundle.items.length} Items)
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {selectedBundle.items.map((item, idx) => (
                    <div
                      key={item.id}
                      style={{
                        padding: 12,
                        backgroundColor: "var(--bg-app)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "var(--radius-sm)",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span
                            style={{
                              width: 18,
                              height: 18,
                              borderRadius: "50%",
                              backgroundColor: "rgba(6, 182, 212, 0.2)",
                              color: "var(--accent-cyan)",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              fontSize: 10,
                              fontFamily: "var(--font-mono)",
                              fontWeight: 700,
                            }}
                          >
                            {idx + 1}
                          </span>
                          <span style={{ fontSize: 11, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>
                            {item.role_in_bundle}
                          </span>
                          <span style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                            ({item.evidence?.evidence_type})
                          </span>
                        </div>
                        {item.evidence && (
                          <span
                            style={{
                              fontSize: 9,
                              fontFamily: "var(--font-mono)",
                              padding: "2px 6px",
                              borderRadius: 3,
                              ...getQualityBadge(item.evidence.quality_state),
                            }}
                          >
                            {item.evidence.quality_state}
                          </span>
                        )}
                      </div>

                      <div style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.4 }}>
                        {item.evidence?.explanation || "Authoritative proof record."}
                      </div>

                      {item.evidence?.value && (
                        <div style={{ marginTop: 8, padding: 6, backgroundColor: "rgba(0, 0, 0, 0.2)", borderRadius: 3, fontSize: 10, fontFamily: "var(--font-mono)" }}>
                          <pre style={{ margin: 0, color: "var(--accent-cyan)" }}>
                            {JSON.stringify(item.evidence.value, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div style={{ padding: 40, textAlign: "center", color: "var(--text-muted)" }}>
                Select an evidence bundle to view its ordered chain of physical and inference proofs.
              </div>
            )}
          </div>
        </div>
      )}
    </AppShell>
  );
}
