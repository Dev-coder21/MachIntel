import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import MaintenancePage from "@/app/maintenance/page";
import { apiClient } from "@/lib/api-client";
import * as authContext from "@/lib/auth-context";
import { MaintenanceWorkOrder, MaintenanceWorkOrderDetail, MaintenanceSummary } from "@/types/maintenance";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/maintenance",
}));

const mockSummary: MaintenanceSummary = {
  total_work_orders: 4,
  open_count: 2,
  acknowledged_count: 1,
  in_progress_count: 0,
  completed_count: 1,
  cancelled_count: 0,
  critical_priority_count: 1,
  high_priority_count: 2,
  medium_priority_count: 1,
  low_priority_count: 0,
  machine_health_count: 3,
  visual_inspection_count: 1,
  recent_activity: [],
};

const mockWorkOrders: MaintenanceWorkOrder[] = [
  {
    id: "wo-001",
    machine_id: "TURBOFAN-ENG-001",
    source_domain: "MACHINE_HEALTH",
    source_type: "RISK_ASSESSMENT",
    source_reference: "risk-uuid-1",
    deduplication_key: "RISK_ASSESSMENT:risk-uuid-1:maintenance-policy-v1.0.0",
    title: "CRITICAL: Machine Health Action Required for TURBOFAN-ENG-001",
    description: "Work order drafted from risk assessment",
    priority: "CRITICAL",
    status: "OPEN",
    recommended_action: "Prioritize human review of the machine-health evidence and assess whether maintenance action is required.",
    reason: "Turbofan exhibits CRITICAL risk state with estimated RUL of 12.5 cycles.",
    risk_state_at_creation: "CRITICAL",
    predicted_rul_at_creation: 12.5,
    health_index_at_creation: 0.15,
    anomaly_score_at_creation: null,
    policy_version: "maintenance-policy-v1.0.0",
    evidence_references: [],
    created_by_id: null,
    assigned_to_id: null,
    created_at: "2026-10-01T08:00:00Z",
    acknowledged_at: null,
    started_at: null,
    completed_at: null,
    cancelled_at: null,
    updated_at: "2026-10-01T08:00:00Z",
    resolution_notes: null,
  },
  {
    id: "wo-002",
    machine_id: null,
    source_domain: "VISUAL_INSPECTION",
    source_type: "INSPECTION_RESULT",
    source_reference: "insp-uuid-2",
    deduplication_key: "INSPECTION_RESULT:insp-uuid-2:maintenance-policy-v1.0.0",
    title: "Inspect Defective Metal Nut (scratch)",
    description: "Visual inspection work order",
    priority: "HIGH",
    status: "OPEN",
    recommended_action: "Review the inspection image, anomaly localization, and benchmark/model evidence before determining the appropriate maintenance or inspection action.",
    reason: "Industrial vision pipeline detected defect class 'scratch' with anomaly score 4.82.",
    risk_state_at_creation: null,
    predicted_rul_at_creation: null,
    health_index_at_creation: null,
    anomaly_score_at_creation: 4.82,
    policy_version: "maintenance-policy-v1.0.0",
    evidence_references: [],
    created_by_id: null,
    assigned_to_id: null,
    created_at: "2026-10-01T08:30:00Z",
    acknowledged_at: null,
    started_at: null,
    completed_at: null,
    cancelled_at: null,
    updated_at: "2026-10-01T08:30:00Z",
    resolution_notes: null,
  },
];

const mockDetail: MaintenanceWorkOrderDetail = {
  ...mockWorkOrders[0],
  events: [
    {
      id: "ev-001",
      work_order_id: "wo-001",
      event_type: "CREATED",
      from_status: null,
      to_status: "OPEN",
      actor_id: null,
      notes: "Work order drafted from operational evidence.",
      event_metadata: {},
      created_at: "2026-10-01T08:00:00Z",
    },
  ],
  source_entity_details: {
    risk_state: "CRITICAL",
    predicted_rul: 12.5,
    health_index: 0.15,
  },
};

describe("MaintenancePage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(apiClient, "getMaintenanceSummary").mockResolvedValue(mockSummary);
    vi.spyOn(apiClient, "listWorkOrders").mockResolvedValue(mockWorkOrders);
    vi.spyOn(apiClient, "getWorkOrderDetail").mockResolvedValue(mockDetail);
  });

  it("renders page header and summary KPI ribbon counts", async () => {
    vi.spyOn(authContext, "useAuth").mockReturnValue({
      user: {
        id: "u-1",
        username: "operator_jane",
        email: "jane@machintel.com",
        full_name: "Jane Operator",
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

    render(<MaintenancePage />);

    expect(screen.getByText("Maintenance Workflow & Operations")).toBeDefined();

    await waitFor(() => {
      expect(screen.getByText("Open Work Orders")).toBeDefined();
      expect(screen.getByText("Critical Priority")).toBeDefined();
      expect(screen.getByText("Completed Outcomes")).toBeDefined();
    });
  });

  it("displays work order queue and detail panel for selected item", async () => {
    vi.spyOn(authContext, "useAuth").mockReturnValue({
      user: {
        id: "u-1",
        username: "operator_jane",
        email: "jane@machintel.com",
        full_name: "Jane Operator",
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

    render(<MaintenancePage />);

    await waitFor(() => {
      expect(screen.getByText("CRITICAL: Machine Health Action Required for TURBOFAN-ENG-001")).toBeDefined();
      expect(screen.getByText("Inspect Defective Metal Nut (scratch)")).toBeDefined();
    });

    // Verify detail panel shows recommended action and non-autonomous warning
    await waitFor(() => {
      expect(screen.getByText("HUMAN DECISION-SUPPORT WORKFLOW:")).toBeDefined();
      expect(screen.getByText("RECOMMENDED ACTION")).toBeDefined();
    });
  });

  it("respects RBAC: allows OPERATOR to see lifecycle transition buttons", async () => {
    vi.spyOn(authContext, "useAuth").mockReturnValue({
      user: {
        id: "u-1",
        username: "operator_jane",
        email: "jane@machintel.com",
        full_name: "Jane Operator",
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

    render(<MaintenancePage />);

    await waitFor(() => {
      expect(screen.getByText("ACKNOWLEDGE WORK ORDER")).toBeDefined();
      expect(screen.getByText("CREATE RECOMMENDATION")).toBeDefined();
    });
  });

  it("respects RBAC: hides mutation buttons for VIEWER role", async () => {
    vi.spyOn(authContext, "useAuth").mockReturnValue({
      user: {
        id: "u-viewer",
        username: "guest_viewer",
        email: "viewer@machintel.com",
        full_name: "Guest Viewer",
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

    render(<MaintenancePage />);

    await waitFor(() => {
      expect(screen.queryByText("CREATE RECOMMENDATION")).toBeNull();
      expect(screen.queryByText("ACKNOWLEDGE WORK ORDER")).toBeNull();
      expect(screen.getByText(/Viewer role: Read-only access/i)).toBeDefined();
    });
  });

  it("handles empty work orders state cleanly", async () => {
    vi.spyOn(apiClient, "listWorkOrders").mockResolvedValue([]);
    vi.spyOn(authContext, "useAuth").mockReturnValue({
      user: {
        id: "u-1",
        username: "operator_jane",
        email: "jane@machintel.com",
        full_name: "Jane Operator",
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

    render(<MaintenancePage />);

    await waitFor(() => {
      expect(screen.getByText("No Matching Work Orders")).toBeDefined();
    });
  });
});
