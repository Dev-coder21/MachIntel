import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import AlertsPage from "@/app/alerts/page";
import { apiClient } from "@/lib/api-client";
import * as authContext from "@/lib/auth-context";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/alerts",
}));

const mockAlerts = [
  {
    id: "alert-001",
    machine_id: "TURBOFAN-ENG-001",
    risk_assessment_id: "risk-001",
    severity: "CRITICAL" as const,
    status: "OPEN" as const,
    title: "Critical Operational Risk: High Degradation (RUL <= 18 cyc)",
    description: "Machine TURBOFAN-ENG-001 has entered CRITICAL risk state (Health Index: 0.120).",
    reason_codes: ["HEALTH_INDEX_CRITICAL", "RUL_BELOW_CRITICAL_THRESHOLD"],
    created_at: "2026-10-01T04:30:00Z",
    acknowledged_at: null,
    resolved_at: null,
    acknowledged_by: null,
    resolved_by: null,
  },
  {
    id: "alert-002",
    machine_id: "TURBOFAN-ENG-002",
    risk_assessment_id: "risk-002",
    severity: "WARNING" as const,
    status: "ACKNOWLEDGED" as const,
    title: "Elevated Operational Risk: Accelerated Degradation",
    description: "Machine TURBOFAN-ENG-002 has entered ELEVATED risk state (Health Index: 0.280).",
    reason_codes: ["HEALTH_INDEX_ELEVATED", "RUL_BELOW_ELEVATED_THRESHOLD"],
    created_at: "2026-10-01T04:00:00Z",
    acknowledged_at: "2026-10-01T04:15:00Z",
    resolved_at: null,
    acknowledged_by: "op-uuid-1",
    resolved_by: null,
  },
];

const mockSummary = {
  total: 2,
  open: 1,
  acknowledged: 1,
  resolved: 0,
  by_severity: {
    INFO: 0,
    WARNING: 1,
    CRITICAL: 1,
  },
};

describe("AlertsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders page header and summary KPI counts", async () => {
    vi.spyOn(authContext, "useAuth").mockReturnValue({
      user: {
        id: "u-1",
        username: "viewer",
        email: "viewer@machintel.com",
        full_name: "Viewer",
        role: "VIEWER",
        is_active: true,
        created_at: "2026-10-01T00:00:00Z",
        updated_at: "2026-10-01T00:00:00Z",
      },
      token: "tok",
      isLoading: false,
      isAuthenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    vi.spyOn(apiClient, "getAlerts").mockResolvedValue({
      alerts: mockAlerts,
      total: 2,
      skip: 0,
      limit: 100,
    });

    vi.spyOn(apiClient, "getAlertSummary").mockResolvedValue(mockSummary);

    render(<AlertsPage />);

    expect(screen.getByText(/Industrial Alert Console/i)).toBeDefined();

    await waitFor(() => {
      expect(screen.getByText("Total Recorded Alerts")).toBeDefined();
      expect(screen.getByText("Active Open Alerts")).toBeDefined();
      expect(screen.getByText("Critical Severity Alerts")).toBeDefined();
      expect(screen.getByText(/VIEWER ACCESS/i)).toBeDefined();
    });
  });

  it("displays alert items and respects RBAC by hiding mutation controls for VIEWER", async () => {
    vi.spyOn(authContext, "useAuth").mockReturnValue({
      user: {
        id: "u-1",
        username: "viewer",
        email: "viewer@machintel.com",
        full_name: "Viewer",
        role: "VIEWER",
        is_active: true,
        created_at: "2026-10-01T00:00:00Z",
        updated_at: "2026-10-01T00:00:00Z",
      },
      token: "tok",
      isLoading: false,
      isAuthenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    vi.spyOn(apiClient, "getAlerts").mockResolvedValue({
      alerts: mockAlerts,
      total: 2,
      skip: 0,
      limit: 100,
    });

    vi.spyOn(apiClient, "getAlertSummary").mockResolvedValue(mockSummary);

    render(<AlertsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Critical Operational Risk: High Degradation/i)).toBeDefined();
      expect(screen.getByText("HEALTH_INDEX_CRITICAL")).toBeDefined();
    });

    // For viewer, buttons "Acknowledge" and "Resolve" must NOT be rendered
    const ackButtons = screen.queryAllByRole("button", { name: /^Acknowledge$/i });
    expect(ackButtons.length).toBe(0);

    const viewerReadOnlyBadges = screen.getAllByText(/Viewer Read-Only/i);
    expect(viewerReadOnlyBadges.length).toBeGreaterThan(0);
  });

  it("allows OPERATOR to see Acknowledge button and open modal", async () => {
    vi.spyOn(authContext, "useAuth").mockReturnValue({
      user: {
        id: "u-2",
        username: "operator",
        email: "op@machintel.com",
        full_name: "Operator",
        role: "OPERATOR",
        is_active: true,
        created_at: "2026-10-01T00:00:00Z",
        updated_at: "2026-10-01T00:00:00Z",
      },
      token: "tok",
      isLoading: false,
      isAuthenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    vi.spyOn(apiClient, "getAlerts").mockResolvedValue({
      alerts: mockAlerts,
      total: 2,
      skip: 0,
      limit: 100,
    });

    vi.spyOn(apiClient, "getAlertSummary").mockResolvedValue(mockSummary);
    vi.spyOn(apiClient, "acknowledgeAlert").mockResolvedValue({
      ...mockAlerts[0],
      status: "ACKNOWLEDGED",
      acknowledged_at: "2026-10-01T04:35:00Z",
      acknowledged_by: "u-2",
    });

    render(<AlertsPage />);

    await waitFor(() => {
      expect(screen.getByText(/OPERATOR ACCESS/i)).toBeDefined();
    });

    const ackButton = screen.getByRole("button", { name: /^Acknowledge$/i });
    expect(ackButton).toBeDefined();

    fireEvent.click(ackButton);

    // Modal should now be open
    expect(screen.getByText("Confirm Acknowledgment")).toBeDefined();
  });
});
