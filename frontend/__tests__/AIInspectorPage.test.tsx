import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import AIInspectorPage from "@/app/ai-inspector/page";
import { apiClient } from "@/lib/api-client";
import * as authContext from "@/lib/auth-context";
import { AIInvestigationResponse, ToolDefinitionSchema } from "@/types/ai-inspector";

// Mock next/navigation
let mockSearchParams = new URLSearchParams("");
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/ai-inspector",
  useSearchParams: () => mockSearchParams,
}));

const mockInvestigationSuccess: AIInvestigationResponse = {
  id: "inv-001-test",
  question: "What is the current health state and evidence for TURBOFAN-ENG-001?",
  status: "COMPLETED",
  answer:
    "Asset TURBOFAN-ENG-001 is currently observed in an ELEVATED risk state at observation cycle 192, with an estimated remaining useful life (RUL) of 34.5 cycles. Risk classification was triggered under risk-policy-v1.0.0 due to high vibration anomalies on sensor 11.",
  evidence: [
    {
      evidence_id: "ev-rec-001",
      domain: "MACHINE_HEALTH",
      type: "RUL_PREDICTION",
      source: "rul_predictions",
      observation_cycle: 192,
      quality_state: "DERIVED",
      explanation: "Estimated 34.5 remaining operational cycles at cycle 192.",
      value_summary: "RUL: 34.5 cycles, HI: 0.42",
    },
    {
      evidence_id: "ev-rec-002",
      domain: "MACHINE_HEALTH",
      type: "RISK_ASSESSMENT",
      source: "risk_assessments",
      observation_cycle: 192,
      quality_state: "DERIVED",
      explanation: "Risk state assessed as ELEVATED based on rule RUL_THRESHOLD.",
      value_summary: "ELEVATED (LOW_RUL_CRITICAL)",
    },
  ],
  limitations: [
    "Predictions are derived from linear regression benchmark models without calibrated individual-asset uncertainty intervals.",
    "Observed telemetry terminates at cycle 192; actual failure point is not directly observed.",
  ],
  investigation: {
    tool_calls: [
      {
        tool_name: "get_machine_health_summary",
        arguments: { machine_id: "TURBOFAN-ENG-001" },
        status: "SUCCESS",
        duration_ms: 12.4,
        evidence_ids_returned: ["ev-rec-001", "ev-rec-002"],
      },
      {
        tool_name: "get_machine_risk",
        arguments: { machine_id: "TURBOFAN-ENG-001" },
        status: "SUCCESS",
        duration_ms: 8.1,
        evidence_ids_returned: ["ev-rec-002"],
      },
    ],
    domains_consulted: ["MACHINE_HEALTH"],
    completed: true,
  },
  provider: "mock",
  model: "deterministic-test",
  created_at: "2026-10-01T12:00:00Z",
  completed_at: "2026-10-01T12:00:02Z",
};

const mockTools: ToolDefinitionSchema[] = [
  {
    name: "get_machine",
    domain: "MACHINE_HEALTH",
    description: "Retrieve machine identity, dataset, source, and operational status.",
    read_only: true,
    parameters: { type: "object", properties: { machine_id: { type: "string" } }, required: ["machine_id"] },
  },
  {
    name: "get_machine_health_summary",
    domain: "MACHINE_HEALTH",
    description: "Retrieve comprehensive machine health summary including latest RUL, HI, and telemetry features.",
    read_only: true,
    parameters: { type: "object", properties: { machine_id: { type: "string" } }, required: ["machine_id"] },
  },
  {
    name: "get_inspection_result",
    domain: "VISUAL_INSPECTION",
    description: "Retrieve visual inspection result, anomaly score, threshold, and localization.",
    read_only: true,
    parameters: { type: "object", properties: { result_id: { type: "string" } }, required: ["result_id"] },
  },
];

describe("AIInspectorPage (M10 Controlled AI Inspector Console)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockSearchParams = new URLSearchParams("");

    vi.spyOn(authContext, "useAuth").mockReturnValue({
      user: {
        id: "u-admin",
        username: "admin",
        email: "admin@machintel.com",
        full_name: "Admin User",
        role: "ADMIN",
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

    vi.spyOn(apiClient, "getInspectorTools").mockResolvedValue(mockTools);
    vi.spyOn(apiClient, "listInvestigations").mockResolvedValue([]);
    vi.spyOn(apiClient, "createInvestigation").mockResolvedValue(mockInvestigationSuccess);
  });

  it("renders the AI Inspector workspace header, safety ribbon, and prompt triggers", async () => {
    render(<AIInspectorPage />);

    expect(screen.getByText("AI Inspector Forensic Investigation")).toBeDefined();
    expect(
      screen.getByText(/GUARDED READ-ONLY ARCHITECTURE:/i)
    ).toBeDefined();

    await waitFor(() => {
      expect(screen.getByText("Why is machine 1 in CRITICAL risk state?")).toBeDefined();
      expect(screen.getByText("What is the latest RUL for TURBOFAN-ENG-001?")).toBeDefined();
    });
  });

  it("populates prompt input and submits when clicking a suggested investigation question", async () => {
    render(<AIInspectorPage />);

    await waitFor(() => {
      expect(screen.getByText("Why is machine 1 in CRITICAL risk state?")).toBeDefined();
    });

    fireEvent.click(screen.getByText("Why is machine 1 in CRITICAL risk state?"));

    await waitFor(() => {
      expect(apiClient.createInvestigation).toHaveBeenCalledWith("Why is machine 1 in CRITICAL risk state?", {
        machine_id: undefined,
        inspection_run_id: undefined,
      });
    });
  });

  it("submits question, triggers investigation, and displays grounded answer, tools trace, citations, and limitations", async () => {
    render(<AIInspectorPage />);

    const input = screen.getByPlaceholderText(/Ask an evidence-grounded question/i);
    fireEvent.change(input, {
      target: { value: "What is the current health state and evidence for TURBOFAN-ENG-001?" },
    });

    const submitBtn = screen.getByRole("button", { name: /INVESTIGATE/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiClient.createInvestigation).toHaveBeenCalledWith(
        "What is the current health state and evidence for TURBOFAN-ENG-001?",
        {
          machine_id: undefined,
          inspection_run_id: undefined,
        }
      );
    });

    // Check Answer
    await waitFor(() => {
      expect(screen.getByText(/Asset TURBOFAN-ENG-001 is currently observed in an ELEVATED risk state/i)).toBeDefined();
    });

    // Check Tool Trace
    expect(screen.getAllByText("get_machine_health_summary()").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("get_machine_risk()").length).toBeGreaterThanOrEqual(1);

    // Check Evidence Citations
    expect(screen.getAllByText("ev-rec-001").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("RUL_PREDICTION").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("ev-rec-002").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("RISK_ASSESSMENT").length).toBeGreaterThanOrEqual(1);

    // Check Limitations
    expect(screen.getByText(/Predictions are derived from linear regression benchmark models/i)).toBeDefined();
  });

  it("displays provider unavailable limitation message when provider is unconfigured", async () => {
    const mockUnavailableResp: AIInvestigationResponse = {
      ...mockInvestigationSuccess,
      id: "inv-unavail-001",
      status: "FAILED",
      answer: "Forensic analysis could not be synthesized: No active AI Inspector provider is configured.",
      evidence: [],
      limitations: [
        "No active AI Inspector LLM provider is configured (AI_INSPECTOR_PROVIDER=none).",
        "Set AI_INSPECTOR_API_KEY in backend environment to enable generative synthesis.",
      ],
      investigation: {
        tool_calls: [],
        domains_consulted: [],
        completed: false,
      },
      provider: "none",
      model: "none",
    };

    vi.spyOn(apiClient, "createInvestigation").mockResolvedValue(mockUnavailableResp);

    render(<AIInspectorPage />);

    const input = screen.getByPlaceholderText(/Ask an evidence-grounded question/i);
    fireEvent.change(input, { target: { value: "Check status" } });
    fireEvent.click(screen.getByRole("button", { name: /INVESTIGATE/i }));

    await waitFor(() => {
      expect(screen.getByText(/Forensic analysis could not be synthesized: No active AI Inspector provider is configured/i)).toBeDefined();
      expect(screen.getByText(/No active AI Inspector LLM provider is configured/i)).toBeDefined();
    });
  });

  it("pre-populates query and machine context from URL search params", async () => {
    mockSearchParams = new URLSearchParams({
      machine_id: "TURBOFAN-ENG-042",
      question: "What is the latest estimated RUL for TURBOFAN-ENG-042?",
    });

    render(<AIInspectorPage />);

    const input = screen.getByPlaceholderText(/Ask an evidence-grounded question/i) as HTMLInputElement;
    expect(input.value).toBe("What is the latest estimated RUL for TURBOFAN-ENG-042?");

    expect(screen.getByText(/Machine: TURBOFAN-ENG-042/i)).toBeDefined();
  });
});
