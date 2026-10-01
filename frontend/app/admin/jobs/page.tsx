"use client";

import React, { useEffect, useState, useCallback } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { apiClient } from "@/lib/api-client";
import { Job, JobListResponse, JobSummary, WorkerHealth } from "@/types/job";
import {
  Activity,
  AlertCircle,
  CheckCircle,
  Clock,
  Layers,
  Play,
  RefreshCw,
  RotateCw,
  Server,
  ShieldAlert,
  XCircle,
} from "lucide-react";

export default function JobMonitorPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [summary, setSummary] = useState<JobSummary | null>(null);
  const [workerHealth, setWorkerHealth] = useState<WorkerHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [userRole, setUserRole] = useState<string>("VIEWER");
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchStatusAndJobs = useCallback(async () => {
    try {
      const [jobsRes, summaryRes, healthRes] = await Promise.all([
        apiClient.getJobs({ status: statusFilter || undefined, limit: 50 }),
        apiClient.getJobSummary(),
        apiClient.getWorkerHealth(),
      ]);
      setJobs(jobsRes.items);
      setSummary(summaryRes);
      setWorkerHealth(healthRes);
    } catch (err) {
      console.error("Failed to load jobs or worker health:", err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    // Read user role from stored session
    try {
      const stored = localStorage.getItem("user");
      if (stored) {
        const u = JSON.parse(stored);
        if (u && u.role) setUserRole(u.role);
      }
    } catch (e) {
      // Ignore
    }

    fetchStatusAndJobs();
    const interval = setInterval(fetchStatusAndJobs, 5000);
    return () => clearInterval(interval);
  }, [fetchStatusAndJobs]);

  const handleTrigger = async (jobType: string) => {
    setTriggering(jobType);
    setActionMessage(null);
    try {
      const res = await apiClient.triggerJob(jobType);
      setActionMessage(`Job ${jobType} enqueued successfully (ID: ${res.id.slice(0, 8)}...)`);
      await fetchStatusAndJobs();
    } catch (err: any) {
      setActionMessage(`Failed to trigger ${jobType}: ${err.message || "Unauthorized"}`);
    } finally {
      setTriggering(null);
    }
  };

  const isOperatorOrAdmin = userRole === "OPERATOR" || userRole === "ADMIN";

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "QUEUED":
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-900/40 text-amber-300 border border-amber-800"><Clock className="w-3 h-3 mr-1" /> QUEUED</span>;
      case "RUNNING":
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-900/40 text-blue-300 border border-blue-800 animate-pulse"><RotateCw className="w-3 h-3 mr-1 animate-spin" /> RUNNING</span>;
      case "SUCCEEDED":
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-900/40 text-emerald-300 border border-emerald-800"><CheckCircle className="w-3 h-3 mr-1" /> SUCCEEDED</span>;
      case "FAILED":
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-rose-900/40 text-rose-300 border border-rose-800"><XCircle className="w-3 h-3 mr-1" /> FAILED</span>;
      default:
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-800 text-slate-400">{status}</span>;
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <Layers className="h-6 w-6 text-indigo-400" />
              <h1 className="text-xl font-bold text-slate-100">Background Jobs & Operational Refresh</h1>
            </div>
            <p className="text-sm text-slate-400 mt-1">
              Deterministic background intelligence materialization, concurrency locks, and worker cluster observability.
            </p>
          </div>
          <button
            onClick={() => fetchStatusAndJobs()}
            disabled={loading}
            className="inline-flex items-center px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-sm text-slate-200 border border-slate-700 transition"
          >
            <RefreshCw className={`w-4 h-4 mr-1.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        {actionMessage && (
          <div className="p-3 rounded bg-indigo-950/60 border border-indigo-800 text-indigo-200 text-sm flex items-center justify-between">
            <span>{actionMessage}</span>
            <button onClick={() => setActionMessage(null)} className="text-slate-400 hover:text-slate-200">×</button>
          </div>
        )}

        {/* Worker Health Banner */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center gap-3">
            <Server className={`w-8 h-8 ${workerHealth?.status === "HEALTHY" ? "text-emerald-400" : "text-amber-400"}`} />
            <div>
              <div className="text-xs font-semibold text-slate-400 uppercase">Worker Status</div>
              <div className="text-base font-bold text-slate-100 flex items-center gap-1.5 mt-0.5">
                <span className={`w-2 h-2 rounded-full ${workerHealth?.status === "HEALTHY" ? "bg-emerald-400 animate-ping" : "bg-amber-400"}`} />
                {workerHealth?.status || "CHECKING"}
              </div>
            </div>
          </div>

          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center gap-3">
            <Activity className="w-8 h-8 text-blue-400" />
            <div>
              <div className="text-xs font-semibold text-slate-400 uppercase">Active Workers</div>
              <div className="text-base font-bold text-slate-100 mt-0.5">
                {workerHealth?.active_workers_count || 0} process(es)
              </div>
            </div>
          </div>

          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center gap-3">
            <Clock className="w-8 h-8 text-purple-400" />
            <div>
              <div className="text-xs font-semibold text-slate-400 uppercase">Scheduler State</div>
              <div className="text-base font-bold text-slate-100 mt-0.5">
                {workerHealth?.scheduler_enabled ? "ENABLED (Periodic)" : "DISABLED"}
              </div>
            </div>
          </div>

          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center gap-3">
            <CheckCircle className="w-8 h-8 text-indigo-400" />
            <div>
              <div className="text-xs font-semibold text-slate-400 uppercase">Database Queue</div>
              <div className="text-base font-bold text-slate-100 mt-0.5">
                {workerHealth?.database_connected ? "CONNECTED (ACID)" : "DISCONNECTED"}
              </div>
            </div>
          </div>
        </div>

        {/* Operational Trigger Panel */}
        <div className="p-5 rounded-lg bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
              Trigger Operational Refresh Jobs
            </h2>
            {!isOperatorOrAdmin && (
              <span className="text-xs text-amber-400 flex items-center gap-1">
                <ShieldAlert className="w-3.5 h-3.5" /> Viewer mode: Mutation disabled
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400">
            Enqueues deterministic jobs to materialize evidence, recalculate risk boundaries, or refresh maintenance work orders from persisted records.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <button
              onClick={() => handleTrigger("EVIDENCE_REFRESH")}
              disabled={!isOperatorOrAdmin || triggering !== null}
              className="flex items-center justify-between p-3 rounded bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-left transition"
            >
              <div>
                <div className="text-xs font-semibold text-slate-100">Evidence Materialization</div>
                <div className="text-[11px] text-slate-400 mt-0.5">EVIDENCE_REFRESH</div>
              </div>
              <Play className={`w-4 h-4 text-emerald-400 ${triggering === "EVIDENCE_REFRESH" ? "animate-spin" : ""}`} />
            </button>

            <button
              onClick={() => handleTrigger("RISK_REFRESH")}
              disabled={!isOperatorOrAdmin || triggering !== null}
              className="flex items-center justify-between p-3 rounded bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-left transition"
            >
              <div>
                <div className="text-xs font-semibold text-slate-100">Risk & Alert Engine</div>
                <div className="text-[11px] text-slate-400 mt-0.5">RISK_REFRESH</div>
              </div>
              <Play className={`w-4 h-4 text-amber-400 ${triggering === "RISK_REFRESH" ? "animate-spin" : ""}`} />
            </button>

            <button
              onClick={() => handleTrigger("MAINTENANCE_RECOMMENDATION_REFRESH")}
              disabled={!isOperatorOrAdmin || triggering !== null}
              className="flex items-center justify-between p-3 rounded bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-left transition"
            >
              <div>
                <div className="text-xs font-semibold text-slate-100">Maintenance Work Orders</div>
                <div className="text-[11px] text-slate-400 mt-0.5">MAINTENANCE_REFRESH</div>
              </div>
              <Play className={`w-4 h-4 text-purple-400 ${triggering === "MAINTENANCE_RECOMMENDATION_REFRESH" ? "animate-spin" : ""}`} />
            </button>

            <button
              onClick={() => handleTrigger("ANALYTICS_REFRESH")}
              disabled={!isOperatorOrAdmin || triggering !== null}
              className="flex items-center justify-between p-3 rounded bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-left transition"
            >
              <div>
                <div className="text-xs font-semibold text-slate-100">Telemetry Completeness</div>
                <div className="text-[11px] text-slate-400 mt-0.5">ANALYTICS_REFRESH</div>
              </div>
              <Play className={`w-4 h-4 text-blue-400 ${triggering === "ANALYTICS_REFRESH" ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Execution KPI Counters */}
        {summary && (
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div className="p-3 rounded bg-slate-900 border border-slate-800 text-center">
              <div className="text-xs text-slate-400">Total Enqueued</div>
              <div className="text-lg font-bold text-slate-100 mt-1">{summary.total_jobs}</div>
            </div>
            <div className="p-3 rounded bg-slate-900 border border-slate-800 text-center">
              <div className="text-xs text-amber-400">Queued</div>
              <div className="text-lg font-bold text-amber-300 mt-1">{summary.queued_count}</div>
            </div>
            <div className="p-3 rounded bg-slate-900 border border-slate-800 text-center">
              <div className="text-xs text-blue-400">Running</div>
              <div className="text-lg font-bold text-blue-300 mt-1">{summary.running_count}</div>
            </div>
            <div className="p-3 rounded bg-slate-900 border border-slate-800 text-center">
              <div className="text-xs text-emerald-400">Succeeded</div>
              <div className="text-lg font-bold text-emerald-300 mt-1">{summary.succeeded_count}</div>
            </div>
            <div className="p-3 rounded bg-slate-900 border border-slate-800 text-center">
              <div className="text-xs text-rose-400">Failed</div>
              <div className="text-lg font-bold text-rose-300 mt-1">{summary.failed_count}</div>
            </div>
          </div>
        )}

        {/* Job Execution Table */}
        <div className="p-5 rounded-lg bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
              Execution History
            </h2>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Filter Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded px-2 py-1"
              >
                <option value="">All Statuses</option>
                <option value="QUEUED">QUEUED</option>
                <option value="RUNNING">RUNNING</option>
                <option value="SUCCEEDED">SUCCEEDED</option>
                <option value="FAILED">FAILED</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300 border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase text-[11px]">
                  <th className="py-2.5 px-3">Job ID</th>
                  <th className="py-2.5 px-3">Job Type</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Attempts</th>
                  <th className="py-2.5 px-3">Duration</th>
                  <th className="py-2.5 px-3">Enqueued At</th>
                  <th className="py-2.5 px-3">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                {jobs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-8 text-slate-500 font-sans">
                      No background jobs recorded in this view.
                    </td>
                  </tr>
                ) : (
                  jobs.map((job) => (
                    <tr key={job.id} className="hover:bg-slate-800/40 transition">
                      <td className="py-2.5 px-3 font-semibold text-slate-200">
                        {job.id.slice(0, 8)}...
                      </td>
                      <td className="py-2.5 px-3 text-slate-100 font-sans font-medium">
                        {job.job_type}
                      </td>
                      <td className="py-2.5 px-3 font-sans">
                        {getStatusBadge(job.status)}
                      </td>
                      <td className="py-2.5 px-3">
                        {job.attempt_count} / {job.max_attempts}
                      </td>
                      <td className="py-2.5 px-3">
                        {job.duration_ms ? `${job.duration_ms} ms` : "—"}
                      </td>
                      <td className="py-2.5 px-3 text-slate-400 font-sans">
                        {new Date(job.created_at).toLocaleTimeString()}
                      </td>
                      <td className="py-2.5 px-3 font-sans">
                        <button
                          onClick={() => setSelectedJob(job)}
                          className="text-xs text-indigo-400 hover:text-indigo-300 underline"
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
        </div>

        {/* Detail Modal */}
        {selectedJob && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
            <div className="bg-slate-900 border border-slate-700 rounded-lg max-w-xl w-full p-5 space-y-4 max-h-[85vh] overflow-y-auto">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-slate-100">Job Execution Details</h3>
                  {getStatusBadge(selectedJob.status)}
                </div>
                <button
                  onClick={() => setSelectedJob(null)}
                  className="text-slate-400 hover:text-slate-200 text-lg font-bold"
                >
                  ×
                </button>
              </div>

              <div className="space-y-2 text-xs">
                <div><span className="text-slate-400">ID:</span> <span className="font-mono text-slate-200">{selectedJob.id}</span></div>
                <div><span className="text-slate-400">Type:</span> <span className="text-slate-200 font-medium">{selectedJob.job_type}</span></div>
                <div><span className="text-slate-400">Execution Key:</span> <span className="font-mono text-slate-200">{selectedJob.execution_key || "None"}</span></div>
                <div><span className="text-slate-400">Worker:</span> <span className="font-mono text-slate-200">{selectedJob.worker_id || "Unassigned"}</span></div>
                <div><span className="text-slate-400">Duration:</span> <span className="text-slate-200">{selectedJob.duration_ms ? `${selectedJob.duration_ms} ms` : "—"}</span></div>
                <div><span className="text-slate-400">Started:</span> <span className="text-slate-200">{selectedJob.started_at ? new Date(selectedJob.started_at).toLocaleString() : "—"}</span></div>
                <div><span className="text-slate-400">Completed:</span> <span className="text-slate-200">{selectedJob.completed_at ? new Date(selectedJob.completed_at).toLocaleString() : "—"}</span></div>
                {selectedJob.error_message && (
                  <div className="p-2 rounded bg-rose-950/60 border border-rose-800 text-rose-300">
                    <span className="font-bold">Error ({selectedJob.error_code}):</span> {selectedJob.error_message}
                  </div>
                )}
              </div>

              <div>
                <div className="text-xs font-semibold text-slate-400 uppercase mb-1">Output Summary</div>
                <pre className="p-3 rounded bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300 overflow-x-auto">
                  {JSON.stringify(selectedJob.output_summary, null, 2)}
                </pre>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  onClick={() => setSelectedJob(null)}
                  className="px-4 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-200 border border-slate-700 transition"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
