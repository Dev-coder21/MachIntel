"use client";

import React, { useEffect, useState, useTransition } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { StatusBadge } from "@/components/common/StatusBadge";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import {
  AIInvestigationResponse,
  AIInvestigationSummary,
  EvidenceCitation,
  InvestigationContext,
  ToolDefinitionSchema,
} from "@/types/ai-inspector";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Clock,
  Compass,
  Database,
  ExternalLink,
  HelpCircle,
  History,
  Layers,
  Search,
  Send,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Terminal,
  XCircle,
} from "lucide-react";

function AIInspectorContent() {
  const { user } = useAuth();
  const searchParams = useSearchParams();

  // URL Query context
  const initialMachineId = searchParams.get("machine_id") || undefined;
  const initialRunId = searchParams.get("run_id") || undefined;
  const initialQuestion = searchParams.get("question") || "";

  const [question, setQuestion] = useState(initialQuestion);
  const [activeContext, setActiveContext] = useState<InvestigationContext>({
    machine_id: initialMachineId,
    inspection_run_id: initialRunId,
  });

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [currentInvestigation, setCurrentInvestigation] = useState<AIInvestigationResponse | null>(null);
  const [investigationHistory, setInvestigationHistory] = useState<AIInvestigationSummary[]>([]);
  const [availableTools, setAvailableTools] = useState<ToolDefinitionSchema[]>([]);
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceCitation | null>(null);

  // Suggested questions
  const suggestedQueries = [
    { label: "Why is machine 1 in CRITICAL risk state?", q: "Why is machine 1 in CRITICAL risk state?" },
    { label: "What is the latest RUL for TURBOFAN-ENG-001?", q: "What is the latest estimated RUL for TURBOFAN-ENG-001?" },
    { label: "What defects were detected in latest inspection?", q: "What defects were detected in the latest metal_nut inspection?" },
    { label: "What open maintenance work orders exist?", q: "What open maintenance work orders are currently active?" },
    { label: "Cross-domain causality test", q: "Did the visual surface defect on the metal nut cause the turbofan engine degradation?" },
  ];

  // Initial load
  useEffect(() => {
    loadTools();
    loadHistory();
  }, []);

  const loadTools = async () => {
    try {
      const tools = await apiClient.getInspectorTools();
      setAvailableTools(tools);
    } catch (err: any) {
      console.error("Failed to load inspector tools:", err);
    }
  };

  const loadHistory = async () => {
    try {
      const history = await apiClient.listInvestigations({ limit: 10 });
      setInvestigationHistory(history);
    } catch (err: any) {
      console.error("Failed to load investigation history:", err);
    }
  };

  const handleSubmit = async (e?: React.FormEvent, customQuery?: string) => {
    if (e) e.preventDefault();
    const queryToRun = customQuery || question;
    if (!queryToRun.trim() || isLoading) return;

    setIsLoading(true);
    setErrorMessage(null);
    setSelectedEvidence(null);

    try {
      const res = await apiClient.createInvestigation(queryToRun, activeContext);
      setCurrentInvestigation(res);
      if (res.evidence.length > 0) {
        setSelectedEvidence(res.evidence[0]);
      }
      loadHistory();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to execute forensic investigation.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectHistoryItem = async (id: string) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const detail = await apiClient.getInvestigation(id);
      setCurrentInvestigation(detail);
      setQuestion(detail.question);
      if (detail.evidence.length > 0) {
        setSelectedEvidence(detail.evidence[0]);
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load investigation record.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AppShell>
      <PageHeader
        title="AI Inspector Forensic Investigation"
        subtitle="Forensic investigative assistant equipped with controlled, read-only tools querying verified application evidence."
        breadcrumbs={[{ label: "Intelligence" }, { label: "AI Inspector" }]}
      />

      {/* Industrial Safety Ribbon */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "10px 16px",
          backgroundColor: "rgba(0, 229, 255, 0.04)",
          border: "1px solid rgba(0, 229, 255, 0.2)",
          borderRadius: "var(--radius-sm)",
          marginBottom: 20,
          fontSize: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <ShieldCheck size={18} style={{ color: "var(--accent-cyan)" }} />
          <span>
            <strong style={{ color: "var(--accent-cyan)", fontFamily: "var(--font-mono)" }}>
              GUARDED READ-ONLY ARCHITECTURE:
            </strong>{" "}
            The AI Inspector possesses zero actuator access, executes zero arbitrary SQL, and enforces strict domain
            separation between NASA C-MAPSS and MVTec AD.
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-muted)", fontFamily: "var(--font-mono)", fontSize: 11 }}>
          <Compass size={14} />
          {availableTools.length} READ-ONLY TOOLS ACTIVE
        </div>
      </div>

      {/* Main Grid: Left / Center (Investigation) | Right (Evidence Inspector & Tool Guardrails) */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 380px",
          gap: 20,
          alignItems: "start",
          marginBottom: 30,
        }}
      >
        {/* Left Column: Inquiry, Activity, and Structured Findings */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Active Context Chips (if preloaded via URL) */}
          {(activeContext.machine_id || activeContext.inspection_run_id) && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "8px 12px",
                backgroundColor: "var(--bg-surface)",
                border: "1px solid var(--border-default)",
                borderRadius: "var(--radius-sm)",
                fontSize: 12,
              }}
            >
              <span style={{ color: "var(--text-muted)" }}>Active Context Filter:</span>
              {activeContext.machine_id && (
                <span
                  style={{
                    padding: "2px 8px",
                    backgroundColor: "rgba(0, 229, 255, 0.1)",
                    border: "1px solid var(--accent-cyan)",
                    color: "var(--accent-cyan)",
                    borderRadius: "var(--radius-sm)",
                    fontFamily: "var(--font-mono)",
                    fontSize: 11,
                  }}
                >
                  Machine: {activeContext.machine_id}
                </span>
              )}
              {activeContext.inspection_run_id && (
                <span
                  style={{
                    padding: "2px 8px",
                    backgroundColor: "rgba(168, 85, 247, 0.1)",
                    border: "1px solid #a855f7",
                    color: "#c084fc",
                    borderRadius: "var(--radius-sm)",
                    fontFamily: "var(--font-mono)",
                    fontSize: 11,
                  }}
                >
                  Run: {activeContext.inspection_run_id.slice(0, 8)}...
                </span>
              )}
              <button
                onClick={() => setActiveContext({})}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  fontSize: 11,
                  marginLeft: "auto",
                }}
              >
                Clear Context
              </button>
            </div>
          )}

          {/* Prompt Submission Card */}
          <div className="tech-card" style={{ padding: 16 }}>
            <form onSubmit={handleSubmit}>
              <div style={{ display: "flex", gap: 10 }}>
                <div style={{ position: "relative", flex: 1 }}>
                  <input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Ask an evidence-grounded question (e.g. 'Why is machine 1 in CRITICAL risk state?')..."
                    disabled={isLoading}
                    style={{
                      width: "100%",
                      padding: "12px 14px",
                      backgroundColor: "var(--bg-app)",
                      border: "1px solid var(--border-default)",
                      borderRadius: "var(--radius-sm)",
                      color: "var(--text-primary)",
                      fontSize: 13,
                      outline: "none",
                      fontFamily: "var(--font-sans)",
                    }}
                  />
                </div>
                <button
                  type="submit"
                  disabled={isLoading || !question.trim()}
                  className="btn btn-primary"
                  style={{
                    padding: "0 20px",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    cursor: isLoading || !question.trim() ? "not-allowed" : "pointer",
                    opacity: isLoading || !question.trim() ? 0.6 : 1,
                  }}
                >
                  <Send size={15} />
                  {isLoading ? "INVESTIGATING..." : "INVESTIGATE"}
                </button>
              </div>
            </form>

            {/* Quick Suggestion Pills */}
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 6 }}>
                Suggested Investigation Questions:
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {suggestedQueries.map((item, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setQuestion(item.q);
                      handleSubmit(undefined, item.q);
                    }}
                    disabled={isLoading}
                    style={{
                      padding: "4px 10px",
                      backgroundColor: "var(--bg-app)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: 12,
                      color: "var(--text-secondary)",
                      fontSize: 11,
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Error Banner */}
          {errorMessage && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "12px 16px",
                backgroundColor: "rgba(239, 68, 68, 0.1)",
                border: "1px solid var(--accent-red)",
                borderRadius: "var(--radius-sm)",
                color: "var(--accent-red)",
                fontSize: 13,
              }}
            >
              <XCircle size={18} />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Investigation Result Area */}
          {isLoading && (
            <div
              className="tech-card"
              style={{
                padding: 40,
                textAlign: "center",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 12,
              }}
            >
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: "50%",
                  border: "3px solid var(--border-default)",
                  borderTopColor: "var(--accent-cyan)",
                  animation: "spin 1s linear infinite",
                }}
              />
              <div style={{ fontSize: 13, fontWeight: 600, color: "var(--accent-cyan)" }}>
                Executing Controlled Read-Only Tool Execution...
              </div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", maxWidth: 360 }}>
                Querying persisted telemetry, predictive models, inspection runs, and evidence records without
                autonomous action.
              </div>
            </div>
          )}

          {!isLoading && currentInvestigation && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {/* Tool Execution Activity Stream */}
              <div
                className="tech-card"
                style={{
                  padding: 14,
                  backgroundColor: "rgba(0, 0, 0, 0.3)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    marginBottom: 10,
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                    color: "var(--text-muted)",
                  }}
                >
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <Terminal size={14} style={{ color: "var(--accent-cyan)" }} />
                    TOOL EXECUTION TRACE ({(currentInvestigation.investigation?.tool_calls || []).length} EXECUTED)
                  </span>
                  <span>PROVIDER: {(currentInvestigation.provider || "SYSTEM").toUpperCase()}</span>
                </div>

                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {(currentInvestigation.investigation?.tool_calls || []).map((t, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                        padding: "4px 8px",
                        backgroundColor: "var(--bg-app)",
                        border: "1px solid var(--border-default)",
                        borderRadius: "var(--radius-sm)",
                        fontSize: 11,
                        fontFamily: "var(--font-mono)",
                      }}
                    >
                      <CheckCircle2 size={12} style={{ color: "var(--accent-green)" }} />
                      <span style={{ color: "var(--accent-cyan)" }}>{t.tool_name}()</span>
                      <span style={{ color: "var(--text-muted)", fontSize: 10 }}>{t.duration_ms}ms</span>
                    </div>
                  ))}
                  {(currentInvestigation.investigation?.tool_calls || []).length === 0 && (
                    <div style={{ fontSize: 11, color: "var(--text-muted)" }}>No external tools invoked.</div>
                  )}
                </div>
              </div>

              {/* Main Structured Findings Card */}
              <div className="tech-card" style={{ padding: 20 }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    borderBottom: "1px solid var(--border-default)",
                    paddingBottom: 12,
                    marginBottom: 14,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <Bot size={20} style={{ color: "var(--accent-cyan)" }} />
                    <span style={{ fontWeight: 600, fontSize: 14 }}>INVESTIGATION FINDINGS</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <StatusBadge
                      status={
                        currentInvestigation.status === "COMPLETED"
                          ? "ONLINE"
                          : currentInvestigation.status === "FAILED"
                          ? "CRITICAL"
                          : "WATCH"
                      }
                      label={currentInvestigation.status}
                    />
                    <span style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                      {new Date(currentInvestigation.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                </div>

                {/* Answer Text */}
                <div
                  style={{
                    fontSize: 14,
                    lineHeight: 1.6,
                    color: "var(--text-primary)",
                    whiteSpace: "pre-line",
                  }}
                >
                  {currentInvestigation.answer}
                </div>

                {/* Operational Limitations Callout */}
                {currentInvestigation.limitations.length > 0 && (
                  <div
                    style={{
                      marginTop: 16,
                      padding: 12,
                      backgroundColor: "rgba(245, 158, 11, 0.05)",
                      border: "1px solid rgba(245, 158, 11, 0.3)",
                      borderRadius: "var(--radius-sm)",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                        fontSize: 12,
                        fontWeight: 600,
                        color: "var(--accent-amber)",
                        marginBottom: 6,
                      }}
                    >
                      <AlertTriangle size={14} />
                      OPERATIONAL LIMITATIONS & UNCERTAINTY:
                    </div>
                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "var(--text-secondary)" }}>
                      {currentInvestigation.limitations.map((lim, idx) => (
                        <li key={idx} style={{ marginBottom: 4 }}>
                          {lim}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Investigation History Drawer */}
              {investigationHistory.length > 0 && (
                <div className="tech-card" style={{ padding: 14 }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      fontSize: 12,
                      fontWeight: 600,
                      color: "var(--text-secondary)",
                      marginBottom: 10,
                    }}
                  >
                    <History size={14} />
                    RECENT INVESTIGATIONS ({investigationHistory.length})
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {investigationHistory.map((item) => (
                      <div
                        key={item.id}
                        onClick={() => handleSelectHistoryItem(item.id)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "8px 10px",
                          backgroundColor:
                            currentInvestigation?.id === item.id ? "rgba(0, 229, 255, 0.08)" : "var(--bg-app)",
                          border: `1px solid ${
                            currentInvestigation?.id === item.id ? "var(--accent-cyan)" : "var(--border-subtle)"
                          }`,
                          borderRadius: "var(--radius-sm)",
                          cursor: "pointer",
                          fontSize: 12,
                        }}
                      >
                        <span style={{ color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "70%" }}>
                          {item.question}
                        </span>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
                            {item.evidence_count} CITATIONS
                          </span>
                          <StatusBadge
                            status={
                              item.status === "COMPLETED"
                                ? "ONLINE"
                                : item.status === "FAILED"
                                ? "CRITICAL"
                                : "WATCH"
                            }
                            label={item.status}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Empty / Intro State */}
          {!isLoading && !currentInvestigation && (
            <div className="tech-card" style={{ padding: 40, textAlign: "center" }}>
              <Terminal size={32} style={{ color: "var(--accent-cyan)", margin: "0 auto 12px" }} />
              <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text-primary)", marginBottom: 6 }}>
                AI Inspector Console Ready
              </div>
              <div style={{ fontSize: 12, color: "var(--text-muted)", maxWidth: 440, margin: "0 auto" }}>
                Ask any question regarding turbofan engine health, RUL prognostics, MVTec AD optical inspection runs, or
                maintenance work orders. All responses are derived from persisted PostgreSQL evidence.
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Evidence Inspector & Read-Only Tool Specifications */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Grounded Evidence Citations Panel */}
          <div className="tech-card" style={{ padding: 16 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: 12,
                fontSize: 12,
                fontWeight: 600,
                color: "var(--accent-cyan)",
              }}
            >
              <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <Layers size={16} />
                GROUNDED EVIDENCE ({currentInvestigation?.evidence.length || 0})
              </span>
            </div>

            {currentInvestigation && currentInvestigation.evidence.length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {currentInvestigation.evidence.map((cit, idx) => (
                  <div
                    key={idx}
                    onClick={() => setSelectedEvidence(cit)}
                    style={{
                      padding: "10px 12px",
                      backgroundColor:
                        selectedEvidence?.evidence_id === cit.evidence_id
                          ? "rgba(0, 229, 255, 0.08)"
                          : "var(--bg-app)",
                      border: `1px solid ${
                        selectedEvidence?.evidence_id === cit.evidence_id
                          ? "var(--accent-cyan)"
                          : "var(--border-subtle)"
                      }`,
                      borderRadius: "var(--radius-sm)",
                      cursor: "pointer",
                      fontSize: 11,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
                      <span
                        style={{
                          padding: "2px 6px",
                          borderRadius: 3,
                          fontSize: 9,
                          fontFamily: "var(--font-mono)",
                          fontWeight: 600,
                          backgroundColor:
                            cit.domain === "MACHINE_HEALTH"
                              ? "rgba(0, 229, 255, 0.15)"
                              : "rgba(168, 85, 247, 0.15)",
                          color: cit.domain === "MACHINE_HEALTH" ? "var(--accent-cyan)" : "#c084fc",
                        }}
                      >
                        {cit.domain}
                      </span>
                      <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-muted)", fontSize: 10 }}>
                        {cit.quality_state}
                      </span>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>
                        {cit.type}
                      </span>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--accent-cyan)" }}>
                        {cit.evidence_id}
                      </span>
                    </div>

                    {cit.explanation && (
                      <div style={{ color: "var(--text-muted)", marginBottom: 6, lineHeight: 1.4 }}>
                        {cit.explanation}
                      </div>
                    )}

                    {cit.value_summary && (
                      <div
                        style={{
                          padding: "4px 6px",
                          backgroundColor: "rgba(0,0,0,0.3)",
                          borderRadius: 3,
                          fontFamily: "var(--font-mono)",
                          fontSize: 10,
                          color: "var(--accent-cyan)",
                        }}
                      >
                        {cit.value_summary}
                      </div>
                    )}

                    {/* Navigation Link to Asset/Inspection */}
                    <div style={{ marginTop: 8, display: "flex", gap: 6 }}>
                      {cit.domain === "MACHINE_HEALTH" ? (
                        <Link
                          href="/machines"
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 4,
                            color: "var(--accent-cyan)",
                            fontSize: 10,
                            textDecoration: "none",
                          }}
                        >
                          View Fleet <ExternalLink size={10} />
                        </Link>
                      ) : (
                        <Link
                          href="/inspections"
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 4,
                            color: "#c084fc",
                            fontSize: 10,
                            textDecoration: "none",
                          }}
                        >
                          View Visual Inspections <ExternalLink size={10} />
                        </Link>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: 11, color: "var(--text-muted)", textAlign: "center", padding: 20 }}>
                No active evidence records in current investigation scope.
              </div>
            )}
          </div>

          {/* Controlled Tool Specifications Box */}
          <div className="tech-card" style={{ padding: 16 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                fontSize: 12,
                fontWeight: 600,
                color: "var(--accent-cyan)",
                marginBottom: 10,
              }}
            >
              <Shield size={16} />
              CONTROLLED TOOL REGISTRY ({availableTools.length})
            </div>

            <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 12 }}>
              Every tool is strictly read-only and validates inputs against SQL injection and path traversal patterns.
            </div>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 8,
                maxHeight: 280,
                overflowY: "auto",
                fontSize: 11,
              }}
            >
              {availableTools.map((t) => (
                <div
                  key={t.name}
                  style={{
                    padding: "6px 8px",
                    backgroundColor: "var(--bg-app)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "var(--radius-sm)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span className="mono-readout" style={{ color: "var(--accent-cyan)", fontWeight: 500 }}>
                      {t.name}()
                    </span>
                    <span
                      style={{
                        padding: "1px 5px",
                        borderRadius: 2,
                        fontSize: 9,
                        fontFamily: "var(--font-mono)",
                        backgroundColor: "rgba(16, 185, 129, 0.15)",
                        color: "var(--accent-green)",
                      }}
                    >
                      READ-ONLY
                    </span>
                  </div>
                  <div style={{ color: "var(--text-muted)", marginTop: 2, fontSize: 10 }}>
                    {t.description}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

export default function AIInspectorPage() {
  return (
    <React.Suspense
      fallback={
        <AppShell>
          <div style={{ padding: 40, textAlign: "center", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
            INITIALIZING FORENSIC INSPECTOR WORKSPACE...
          </div>
        </AppShell>
      }
    >
      <AIInspectorContent />
    </React.Suspense>
  );
}
