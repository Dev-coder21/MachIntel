import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import JobMonitorPage from "@/app/admin/jobs/page";
import { apiClient } from "@/lib/api-client";
import * as authContext from "@/lib/auth-context";
import { Job, JobListResponse, JobSummary, WorkerHealth } from "@/types/job";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/admin/jobs",
}));

const mockWorkerHealth: WorkerHealth = {
  status: "HEALTHY",
  worker_enabled: true,
  scheduler_enabled: true,
  database_connected: true,
  active_workers_count: 1,
  active_workers: [
    {
      worker_id: "worker-test-1",
      hostname: "localhost",
      pid: 12345,
      status: "ACTIVE",
      started_at: "2026-10-01T08:00:00Z",
      heartbeat_at: "2026-10-01T08:05:00Z",
      current_job_id: null,
    },
  ],
  timestamp: "2026-10-01T08:05:00Z",
};

const mockSummary: JobSummary = {
  total_jobs: 5,
  queued_count: 1,
  running_count: 1,
  succeeded_count: 2,
  failed_count: 1,
  cancelled_count: 0,
  recent_jobs: [],
  last_refresh_by_type: {
    EVIDENCE_REFRESH: "2026-10-01T07:30:00Z",
    RISK_REFRESH: "2026-10-01T07:45:00Z",
    MAINTENANCE_RECOMMENDATION_REFRESH: null,
    ANALYTICS_REFRESH: "2026-10-01T08:00:00Z",
  },
  active_workers_count: 1,
};

const mockJobs: Job[] = [
  {
    id: "job-001-uuid",
    job_type: "EVIDENCE_REFRESH",
    status: "SUCCEEDED",
    execution_key: "EVIDENCE_REFRESH:fleet",
    requested_by_id: null,
    attempt_count: 1,
    max_attempts: 3,
    error_code: null,
    error_message: null,
    payload: {},
    output_summary: { evidence_created: 10, relationships_created: 15 },
    retry_metadata: {},
    worker_id: "worker-test-1",
    duration_ms: 125.4,
    created_at: "2026-10-01T07:30:00Z",
    started_at: "2026-10-01T07:30:01Z",
    completed_at: "2026-10-01T07:30:02Z",
    heartbeat_at: "2026-10-01T07:30:02Z",
  },
  {
    id: "job-002-uuid",
    job_type: "RISK_REFRESH",
    status: "RUNNING",
    execution_key: "RISK_REFRESH:fleet",
    requested_by_id: null,
    attempt_count: 1,
    max_attempts: 3,
    error_code: null,
    error_message: null,
    payload: {},
    output_summary: {},
    retry_metadata: {},
    worker_id: "worker-test-1",
    duration_ms: null,
    created_at: "2026-10-01T08:00:00Z",
    started_at: "2026-10-01T08:00:01Z",
    completed_at: null,
    heartbeat_at: "2026-10-01T08:00:05Z",
  },
];

describe("JobMonitorPage (M12 Background Jobs & Workers)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.setItem("user", JSON.stringify({ username: "operator_user", role: "OPERATOR" }));

    vi.spyOn(authContext, "useAuth").mockReturnValue({
      user: {
        id: "u-operator",
        username: "operator_user",
        email: "op@machintel.com",
        full_name: "Operator User",
        role: "OPERATOR",
        is_active: true,
        created_at: "2026-10-01T00:00:00Z",
        updated_at: "2026-10-01T00:00:00Z",
      },
      token: "mock-token",
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    vi.spyOn(apiClient, "getWorkerHealth").mockResolvedValue(mockWorkerHealth);
    vi.spyOn(apiClient, "getJobSummary").mockResolvedValue(mockSummary);
    vi.spyOn(apiClient, "getJobs").mockResolvedValue({
      items: mockJobs,
      total: 2,
      skip: 0,
      limit: 50,
    });
  });

  it("renders page header and worker health banner", async () => {
    render(<JobMonitorPage />);

    expect(screen.getByText("Background Jobs & Operational Refresh")).toBeDefined();

    await waitFor(() => {
      expect(screen.getByText("HEALTHY")).toBeDefined();
      expect(screen.getByText("1 process(es)")).toBeDefined();
      expect(screen.getByText("ENABLED (Periodic)")).toBeDefined();
    });
  });

  it("renders summary KPI counts correctly", async () => {
    render(<JobMonitorPage />);

    await waitFor(() => {
      expect(screen.getByText("5")).toBeDefined(); // total jobs
      expect(screen.getByText("Queued")).toBeDefined();
      expect(screen.getByText("Running")).toBeDefined();
      expect(screen.getByText("Succeeded")).toBeDefined();
    });
  });

  it("renders job execution table with jobs and badges", async () => {
    render(<JobMonitorPage />);

    await waitFor(() => {
      expect(screen.getByText("job-001-...")).toBeDefined();
      expect(screen.getAllByText("EVIDENCE_REFRESH").length).toBeGreaterThanOrEqual(2);
      expect(screen.getAllByText("SUCCEEDED").length).toBeGreaterThanOrEqual(1);

      expect(screen.getByText("job-002-...")).toBeDefined();
      expect(screen.getAllByText("RISK_REFRESH").length).toBeGreaterThanOrEqual(2);
      expect(screen.getAllByText("RUNNING").length).toBeGreaterThanOrEqual(1);
    });
  });

  it("opens job details modal on inspect click", async () => {
    render(<JobMonitorPage />);

    await waitFor(() => {
      expect(screen.getAllByText("Inspect").length).toBe(2);
    });

    fireEvent.click(screen.getAllByText("Inspect")[0]);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Job Execution Details" })).toBeDefined();
      expect(screen.getByText("Execution Key:")).toBeDefined();
      expect(screen.getAllByText("125.4 ms").length).toBeGreaterThanOrEqual(2);
    });

    fireEvent.click(screen.getByText("Close"));
    await waitFor(() => {
      expect(screen.queryByRole("heading", { name: "Job Execution Details" })).toBeNull();
    });
  });

  it("allows operator to trigger a refresh job", async () => {
    vi.spyOn(apiClient, "triggerJob").mockResolvedValue({
      ...mockJobs[0],
      id: "new-triggered-uuid",
      job_type: "ANALYTICS_REFRESH",
      status: "QUEUED",
    });

    render(<JobMonitorPage />);

    await waitFor(() => {
      expect(screen.getByText("Telemetry Completeness")).toBeDefined();
    });

    const triggerButton = screen.getByText("Telemetry Completeness").closest("button");
    expect((triggerButton as HTMLButtonElement).disabled).toBe(false);

    fireEvent.click(triggerButton!);

    await waitFor(() => {
      expect(apiClient.triggerJob).toHaveBeenCalledWith("ANALYTICS_REFRESH");
    });
  });

  it("disables trigger buttons in Viewer mode", async () => {
    localStorage.setItem("user", JSON.stringify({ username: "viewer_user", role: "VIEWER" }));
    vi.spyOn(authContext, "useAuth").mockReturnValue({
      user: {
        id: "u-viewer",
        username: "viewer_user",
        email: "viewer@machintel.com",
        full_name: "Viewer User",
        role: "VIEWER",
        is_active: true,
        created_at: "2026-10-01T00:00:00Z",
        updated_at: "2026-10-01T00:00:00Z",
      },
      token: "mock-token",
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    render(<JobMonitorPage />);

    await waitFor(() => {
      expect(screen.getByText(/Viewer mode: Mutation disabled/i)).toBeDefined();
    });

    const triggerButton = screen.getByText("Evidence Materialization").closest("button");
    expect((triggerButton as HTMLButtonElement).disabled).toBe(true);
  });
});
