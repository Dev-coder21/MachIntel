import React from "react";
import { RiskAssessmentItem } from "@/types/risk";
import { StatusBadge } from "@/components/common/StatusBadge";
import { ArrowRight, CheckCircle2, ShieldAlert, Cpu, Database, Activity, FileCode } from "lucide-react";

interface EvidenceChainProps {
  assessment: RiskAssessmentItem;
  className?: string;
}

export const EvidenceChain: React.FC<EvidenceChainProps> = ({ assessment, className = "" }) => {
  return (
    <div
      className={`panel ${className}`}
      style={{
        padding: 20,
        backgroundColor: "var(--bg-surface)",
        border: "1px solid var(--border-default)",
        borderRadius: "var(--radius-md)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 8 }}>
            <Activity size={16} color="var(--accent-cyan)" />
            Deterministic Evidence Chain
          </div>
          <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
            Traceable causal inference path from raw C-MAPSS telemetry cycles to deterministic risk state.
          </div>
        </div>
        <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", backgroundColor: "rgba(255,255,255,0.03)", padding: "4px 8px", borderRadius: 4, border: "1px solid var(--border-subtle)" }}>
          POLICY: {assessment.policy_version}
        </div>
      </div>

      {/* Visual Chain Flow */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
          gap: 12,
          padding: "16px 12px",
          backgroundColor: "rgba(0, 0, 0, 0.25)",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--border-subtle)",
          marginBottom: 20,
        }}
      >
        {/* Node 1: Telemetry Provenance */}
        <div style={{ textAlign: "center", padding: 8 }}>
          <div style={{ display: "flex", justifyContent: "center", marginBottom: 6 }}>
            <Database size={20} color="var(--accent-cyan)" />
          </div>
          <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Telemetry Source
          </div>
          <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)", marginTop: 2 }}>
            C-MAPSS FD001
          </div>
          <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
            Causal Window (W=20)
          </div>
        </div>

        {/* Node 2: ML Model Version */}
        <div style={{ textAlign: "center", padding: 8, borderLeft: "1px solid var(--border-subtle)" }}>
          <div style={{ display: "flex", justifyContent: "center", marginBottom: 6 }}>
            <Cpu size={20} color="#A78BFA" />
          </div>
          <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Prognostic Model
          </div>
          <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)", marginTop: 2 }}>
            Ridge Regressor
          </div>
          <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
            rul-ridge-v1.0.0
          </div>
        </div>

        {/* Node 3: Estimated RUL */}
        <div style={{ textAlign: "center", padding: 8, borderLeft: "1px solid var(--border-subtle)" }}>
          <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Estimated RUL
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--text-primary)", marginTop: 4 }}>
            {assessment.predicted_rul.toFixed(1)}
          </div>
          <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>
            operating cycles
          </div>
        </div>

        {/* Node 4: Health Index */}
        <div style={{ textAlign: "center", padding: 8, borderLeft: "1px solid var(--border-subtle)" }}>
          <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)", textTransform: "uppercase" }}>
            Health Index
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--accent-cyan)", marginTop: 4 }}>
            {assessment.health_index.toFixed(3)}
          </div>
          <div style={{ fontSize: 10, color: "var(--text-secondary)" }}>
            HI = clamp(RUL/125, 0, 1)
          </div>
        </div>

        {/* Node 5: Risk State */}
        <div style={{ textAlign: "center", padding: 8, borderLeft: "1px solid var(--border-subtle)" }}>
          <div style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 6 }}>
            Risk State
          </div>
          <div>
            <StatusBadge status={assessment.risk_state} />
          </div>
          <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 4, fontFamily: "var(--font-mono)" }}>
            Deterministic Policy
          </div>
        </div>
      </div>

      {/* Human-Readable Explanation */}
      <div
        style={{
          padding: "12px 16px",
          backgroundColor: "rgba(255, 255, 255, 0.02)",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--border-subtle)",
          marginBottom: 16,
        }}
      >
        <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 4 }}>
          OPERATIONAL INTERPRETATION & EXPLANATION
        </div>
        <p style={{ fontSize: 13, lineHeight: 1.5, color: "var(--text-primary)", margin: 0 }}>
          {assessment.explanation}
        </p>
      </div>

      {/* Triggered Reason Codes */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 8 }}>
          TRIGGERED REASON CODES ({assessment.reason_codes.length})
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {assessment.reason_codes.map((code) => (
            <span
              key={code}
              style={{
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                fontWeight: 600,
                color:
                  assessment.risk_state === "CRITICAL"
                    ? "var(--risk-critical)"
                    : assessment.risk_state === "ELEVATED"
                    ? "var(--risk-elevated)"
                    : assessment.risk_state === "WATCH"
                    ? "var(--risk-watch)"
                    : "var(--risk-normal)",
                backgroundColor: "rgba(255, 255, 255, 0.04)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-sm)",
                padding: "4px 10px",
              }}
            >
              {code}
            </span>
          ))}
        </div>
      </div>

      {/* Persisted Evidence Objects */}
      {assessment.evidence_references && assessment.evidence_references.length > 0 && (
        <div>
          <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-muted)", marginBottom: 8 }}>
            PERSISTED EVIDENCE RECORDS ({assessment.evidence_references.length})
          </div>
          <div style={{ display: "grid", gap: 8 }}>
            {assessment.evidence_references.map((ev) => (
              <div
                key={ev.evidence_id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "8px 12px",
                  borderRadius: 4,
                  backgroundColor: "rgba(0, 0, 0, 0.2)",
                  border: "1px solid var(--border-subtle)",
                  fontSize: 12,
                }}
              >
                <div>
                  <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600, color: "var(--text-primary)", marginRight: 8 }}>
                    {ev.evidence_type}
                  </span>
                  <span style={{ color: "var(--text-muted)", fontSize: 11, fontFamily: "var(--font-mono)" }}>
                    Source: {ev.source} ({ev.source_reference})
                  </span>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: "var(--accent-cyan)" }}>
                    {typeof ev.value === "number" ? ev.value.toFixed(2) : String(ev.value)} {ev.unit || ""}
                  </span>
                  <span style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                    Confidence: {ev.confidence !== null ? `${(ev.confidence * 100).toFixed(0)}%` : "Uncalibrated / None"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
