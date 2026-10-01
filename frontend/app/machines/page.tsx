"use client";

import React, { useEffect, useState, useTransition } from "react";
import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { StatusBadge } from "@/components/common/StatusBadge";
import { EmptyState } from "@/components/common/EmptyState";
import { apiClient, ApiClientError } from "@/lib/api-client";
import { Machine, SplitCategory, MachineStatus } from "@/types/machine";
import {
  Activity,
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  Database,
  Layers,
  RefreshCw,
  Search,
  SlidersHorizontal,
} from "lucide-react";

export default function MachinesPage() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const pageSize = 20;

  const [searchTerm, setSearchTerm] = useState<string>("");
  const [splitFilter, setSplitFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const fetchMachines = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const skip = (page - 1) * pageSize;
      const res = await apiClient.getMachines({
        skip,
        limit: pageSize,
        search: searchTerm.trim() || undefined,
        split_category: splitFilter !== "ALL" ? splitFilter : undefined,
        status: statusFilter !== "ALL" ? statusFilter : undefined,
      });
      setMachines(res.items);
      setTotal(res.total);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError("Failed to load machine registry from backend.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMachines();
  }, [page, splitFilter, statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchMachines();
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  const getSplitBadgeColor = (split: SplitCategory) => {
    switch (split) {
      case "INTERNAL_TRAIN":
        return { bg: "rgba(0, 229, 255, 0.1)", text: "var(--accent-cyan)", border: "rgba(0, 229, 255, 0.25)", label: "INTERNAL TRAIN" };
      case "INTERNAL_VAL":
        return { bg: "rgba(168, 85, 247, 0.1)", text: "#C084FC", border: "rgba(168, 85, 247, 0.25)", label: "INTERNAL VAL" };
      case "EVAL_TEST":
        return { bg: "rgba(245, 158, 11, 0.1)", text: "#FBBF24", border: "rgba(245, 158, 11, 0.25)", label: "HELD-OUT EVAL" };
      default:
        return { bg: "rgba(148, 163, 184, 0.1)", text: "var(--text-muted)", border: "var(--border-subtle)", label: split };
    }
  };

  return (
    <AppShell>
      <PageHeader
        title="Industrial Machine Registry"
        subtitle="Authoritative machine inventory ingested from NASA C-MAPSS FD001 run-to-failure & test turbofan engines."
        breadcrumbs={[{ label: "Operations" }, { label: "Machine Registry" }]}
        badge={
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              padding: "4px 10px",
              backgroundColor: "rgba(0, 229, 255, 0.08)",
              border: "1px solid rgba(0, 229, 255, 0.2)",
              borderRadius: "var(--radius-sm)",
              fontSize: 11,
              fontFamily: "var(--font-mono)",
              color: "var(--accent-cyan)",
            }}
          >
            <Database size={13} />
            <span>{total} REAL ASSETS REGISTERED</span>
          </div>
        }
      />

      {/* Search & Filter Toolbar */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 12,
          marginBottom: 20,
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        {/* Search Input */}
        <form
          onSubmit={handleSearchSubmit}
          style={{
            flex: "1 1 300px",
            maxWidth: 420,
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "8px 14px",
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          <Search size={15} color="var(--text-muted)" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by Machine ID (e.g. TURBOFAN-ENG-001)..."
            style={{
              flex: 1,
              background: "none",
              border: "none",
              outline: "none",
              color: "var(--text-primary)",
              fontSize: 13,
            }}
          />
          <button
            type="submit"
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "var(--accent-cyan)",
              fontSize: 11,
              fontFamily: "var(--font-mono)",
              fontWeight: 600,
            }}
          >
            FILTER
          </button>
        </form>

        {/* Split Policy Segmented Filter */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 4,
            padding: 3,
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          <span
            style={{
              fontSize: 10,
              fontFamily: "var(--font-mono)",
              color: "var(--text-muted)",
              padding: "0 8px",
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <Layers size={11} /> SPLIT:
          </span>
          {[
            { id: "ALL", label: "All (200)" },
            { id: "INTERNAL_TRAIN", label: "Train (1–80)" },
            { id: "INTERNAL_VAL", label: "Val (81–100)" },
            { id: "EVAL_TEST", label: "Test (1–100)" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setSplitFilter(tab.id);
                setPage(1);
              }}
              style={{
                padding: "5px 10px",
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                fontWeight: splitFilter === tab.id ? 600 : 400,
                color: splitFilter === tab.id ? "var(--accent-cyan)" : "var(--text-secondary)",
                backgroundColor: splitFilter === tab.id ? "rgba(0, 229, 255, 0.12)" : "transparent",
                border: "none",
                borderRadius: "var(--radius-xs)",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Refresh Button */}
        <button
          onClick={fetchMachines}
          title="Refresh Registry"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            padding: "8px 12px",
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-sm)",
            color: "var(--text-secondary)",
            fontSize: 12,
            fontFamily: "var(--font-mono)",
            cursor: "pointer",
          }}
        >
          <RefreshCw size={13} className={isLoading ? "spin" : ""} />
          REFRESH
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div
          style={{
            padding: "14px 18px",
            backgroundColor: "rgba(239, 68, 68, 0.1)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: "var(--radius-sm)",
            color: "var(--risk-critical)",
            fontSize: 13,
            marginBottom: 20,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>Error: {error}</span>
          <button
            onClick={fetchMachines}
            style={{
              padding: "4px 10px",
              backgroundColor: "rgba(239, 68, 68, 0.2)",
              border: "1px solid rgba(239, 68, 68, 0.4)",
              borderRadius: "var(--radius-xs)",
              color: "#FFF",
              fontSize: 11,
              fontFamily: "var(--font-mono)",
              cursor: "pointer",
            }}
          >
            RETRY
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading && machines.length === 0 && (
        <div className="tech-card" style={{ padding: 40, textAlign: "center" }}>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 10, color: "var(--accent-cyan)", fontFamily: "var(--font-mono)", fontSize: 13 }}>
            <RefreshCw size={16} className="spin" />
            QUERYING POSTGRESQL MACHINE REGISTRY...
          </div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && machines.length === 0 && !error && (
        <EmptyState
          icon="database"
          metadataTag="NO MATCHING ASSETS"
          title="No Machines Found"
          description={
            searchTerm || splitFilter !== "ALL"
              ? "No machine entities match your active search terms or split filter criteria. Try resetting the filters."
              : "The machine registry table in PostgreSQL contains no entries."
          }
        >
          {(searchTerm || splitFilter !== "ALL") && (
            <button
              onClick={() => {
                setSearchTerm("");
                setSplitFilter("ALL");
                setPage(1);
              }}
              style={{
                marginTop: 16,
                padding: "8px 16px",
                backgroundColor: "var(--accent-cyan)",
                color: "#05070A",
                border: "none",
                borderRadius: "var(--radius-sm)",
                fontSize: 12,
                fontWeight: 600,
                fontFamily: "var(--font-mono)",
                cursor: "pointer",
              }}
            >
              RESET FILTERS
            </button>
          )}
        </EmptyState>
      )}

      {/* Machine Data Table */}
      {machines.length > 0 && (
        <div
          style={{
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-sm)",
            overflow: "hidden",
            marginBottom: 20,
          }}
        >
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: 13 }}>
              <thead>
                <tr
                  style={{
                    backgroundColor: "rgba(255, 255, 255, 0.02)",
                    borderBottom: "1px solid var(--border-default)",
                    color: "var(--text-muted)",
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                    letterSpacing: "0.05em",
                  }}
                >
                  <th style={{ padding: "12px 16px" }}>ASSET IDENTIFIER</th>
                  <th style={{ padding: "12px 16px" }}>SOURCE IDENTITY</th>
                  <th style={{ padding: "12px 16px" }}>SPLIT POLICY</th>
                  <th style={{ padding: "12px 16px" }}>RECORDED CYCLES</th>
                  <th style={{ padding: "12px 16px" }}>LIFECYCLE STATUS</th>
                  <th style={{ padding: "12px 16px" }}>EVALUATION GROUND TRUTH</th>
                  <th style={{ padding: "12px 16px", textAlign: "right" }}>ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {machines.map((machine) => {
                  const splitBadge = getSplitBadgeColor(machine.split_category);
                  const isTest = machine.split_category === "EVAL_TEST";

                  return (
                    <tr
                      key={machine.id}
                      style={{
                        borderBottom: "1px solid var(--border-subtle)",
                        transition: "background-color 0.15s ease",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.03)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = "transparent";
                      }}
                    >
                      {/* Asset ID */}
                      <td style={{ padding: "14px 16px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <Activity size={14} color="var(--accent-cyan)" />
                          <div>
                            <Link
                              href={`/machines/${machine.machine_id}`}
                              style={{
                                color: "var(--text-primary)",
                                fontWeight: 600,
                                fontFamily: "var(--font-mono)",
                                textDecoration: "none",
                              }}
                            >
                              {machine.machine_id}
                            </Link>
                            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                              {machine.name}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Source Identity */}
                      <td style={{ padding: "14px 16px" }}>
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-secondary)" }}>
                          {machine.source_dataset}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                          Unit #{machine.source_entity_id}
                        </div>
                      </td>

                      {/* Split Category */}
                      <td style={{ padding: "14px 16px" }}>
                        <span
                          style={{
                            display: "inline-block",
                            padding: "3px 8px",
                            backgroundColor: splitBadge.bg,
                            color: splitBadge.text,
                            border: `1px solid ${splitBadge.border}`,
                            borderRadius: "var(--radius-xs)",
                            fontSize: 10,
                            fontFamily: "var(--font-mono)",
                            fontWeight: 600,
                          }}
                        >
                          {splitBadge.label}
                        </span>
                      </td>

                      {/* Cycles Recorded */}
                      <td style={{ padding: "14px 16px" }}>
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--text-primary)" }}>
                          {machine.total_cycles} cycles
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                          Max Cycle: {machine.max_cycle}
                        </div>
                      </td>

                      {/* Status */}
                      <td style={{ padding: "14px 16px" }}>
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
                      </td>

                      {/* Ground Truth RUL / Evaluation */}
                      <td style={{ padding: "14px 16px" }}>
                        {isTest && machine.ground_truth_rul !== null && machine.ground_truth_rul !== undefined ? (
                          <div style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "3px 8px", backgroundColor: "rgba(245, 158, 11, 0.08)", border: "1px solid rgba(245, 158, 11, 0.2)", borderRadius: "var(--radius-xs)" }}>
                            <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "#FBBF24" }}>
                              RUL: {machine.ground_truth_rul} cycles
                            </span>
                            <span style={{ fontSize: 10, color: "var(--text-muted)" }}>(Ground Truth)</span>
                          </div>
                        ) : (
                          <span style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                            Run-to-failure series (Train/Val)
                          </span>
                        )}
                      </td>

                      {/* Actions */}
                      <td style={{ padding: "14px 16px", textAlign: "right" }}>
                        <Link
                          href={`/machines/${machine.machine_id}`}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 6,
                            padding: "6px 12px",
                            backgroundColor: "rgba(0, 229, 255, 0.08)",
                            color: "var(--accent-cyan)",
                            border: "1px solid rgba(0, 229, 255, 0.25)",
                            borderRadius: "var(--radius-xs)",
                            fontSize: 11,
                            fontFamily: "var(--font-mono)",
                            fontWeight: 600,
                            textDecoration: "none",
                            transition: "all 0.15s ease",
                          }}
                        >
                          INVESTIGATE
                          <ArrowRight size={12} />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          <div
            style={{
              padding: "12px 16px",
              backgroundColor: "rgba(255, 255, 255, 0.01)",
              borderTop: "1px solid var(--border-default)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              fontSize: 12,
              color: "var(--text-muted)",
              fontFamily: "var(--font-mono)",
            }}
          >
            <div>
              Showing {total === 0 ? 0 : (page - 1) * pageSize + 1}–
              {Math.min(page * pageSize, total)} of {total} machines
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <button
                disabled={page <= 1 || isLoading}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                  padding: "5px 10px",
                  backgroundColor: "var(--bg-app)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-xs)",
                  color: page <= 1 ? "var(--text-muted)" : "var(--text-primary)",
                  cursor: page <= 1 ? "not-allowed" : "pointer",
                  fontSize: 11,
                }}
              >
                <ChevronLeft size={13} />
                PREV
              </button>

              <span style={{ padding: "0 6px" }}>
                PAGE {page} OF {totalPages}
              </span>

              <button
                disabled={page >= totalPages || isLoading}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                  padding: "5px 10px",
                  backgroundColor: "var(--bg-app)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "var(--radius-xs)",
                  color: page >= totalPages ? "var(--text-muted)" : "var(--text-primary)",
                  cursor: page >= totalPages ? "not-allowed" : "pointer",
                  fontSize: 11,
                }}
              >
                NEXT
                <ChevronRight size={13} />
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
