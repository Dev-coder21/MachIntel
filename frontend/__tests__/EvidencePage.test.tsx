import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import EvidencePage from "@/app/evidence/page";
import { apiClient } from "@/lib/api-client";
import * as authContext from "@/lib/auth-context";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/evidence",
  useSearchParams: () => new URLSearchParams(""),
}));

const mockEvidenceRecords = [
  {
    id: "ev-001",
    domain: "MACHINE_HEALTH",
    entity_type: "MACHINE",
    entity_id: "TURBOFAN-ENG-001",
    evidence_type: "TELEMETRY",
    source: "telemetry_records",
    source_reference: "machine_id=TURBOFAN-ENG-001,cycle=192",
    observation_cycle: 192,
    observation_time: null,
    value: { max_cycle: 192, operational_settings_count: 3, sensor_count: 21 },
    unit: null,
    confidence: null,
    quality_state: "VERIFIED",
    explanation: "Telemetry cycle 192 recorded for asset TURBOFAN-ENG-001.",
    provenance: { dataset: "NASA-C-MAPSS-FD001" },
    model_version: null,
    feature_version: null,
    policy_version: null,
    created_at: "2026-10-01T12:00:00Z",
  },
  {
    id: "ev-002",
    domain: "MACHINE_HEALTH",
    entity_type: "PREDICTION",
    entity_id: "pred-001",
    evidence_type: "RUL_PREDICTION",
    source: "rul_predictions",
    source_reference: "prediction_id=pred-001",
    observation_cycle: 192,
    observation_time: null,
    value: { predicted_rul: 34.5, operational_state: "DEGRADED" },
    unit: "cycles",
    confidence: null,
    quality_state: "DERIVED",
    explanation: "Estimated 34.5 remaining cycles for asset TURBOFAN-ENG-001.",
    provenance: { model_version: "cmapss-rul-linear-v1.0.0" },
    model_version: "cmapss-rul-linear-v1.0.0",
    feature_version: "feature-config-v1.0.0",
    policy_version: null,
    created_at: "2026-10-01T12:01:00Z",
  },
];

const mockVisualEvidenceRecords = [
  {
    id: "ev-vis-001",
    domain: "VISUAL_INSPECTION",
    entity_type: "INSPECTION_RESULT",
    entity_id: "res-001",
    evidence_type: "ANOMALY_SCORE",
    source: "inspection_results",
    source_reference: "result_id=res-001",
    observation_cycle: null,
    observation_time: "2026-10-01T10:00:00Z",
    value: { anomaly_score: 3.42, threshold: 2.8155, decision: "DEFECT" },
    unit: "distance",
    confidence: null,
    quality_state: "DERIVED",
    explanation: "Anomaly score 3.42 exceeds threshold 2.8155, resulting in DEFECT decision.",
    provenance: { model: "PatchCore-WideResNet50" },
    model_version: "mvtec-patchcore-metalnut-v1.0.0",
    feature_version: "cv-feature-config-v1.0.0",
    policy_version: "cv-policy-v1.0.0",
    created_at: "2026-10-01T10:00:00Z",
  },
];

const mockRelationships = [
  {
    id: "rel-001",
    source_evidence_id: "ev-002",
    target_evidence_id: "ev-001",
    relationship_type: "DERIVED_FROM",
    description: "RUL Prediction derived from telemetry feature set",
    created_at: "2026-10-01T12:01:00Z",
  },
];

const mockBundles = [
  {
    id: "bundle-001",
    domain: "MACHINE_HEALTH",
    bundle_name: "Machine Health Bundle - TURBOFAN-ENG-001",
    description: "Deterministic causal bundle for asset TURBOFAN-ENG-001",
    primary_entity_type: "MACHINE",
    primary_entity_id: "TURBOFAN-ENG-001",
    evidence_count: 5,
    items: [],
    created_at: "2026-10-01T12:00:00Z",
  },
];

describe("EvidencePage (M8 Evidence Intelligence Workspace)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
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
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
      isAuthenticated: true,
      isLoading: false,
    });

    vi.spyOn(apiClient, "searchEvidence").mockResolvedValue({
      total: mockEvidenceRecords.length,
      records: mockEvidenceRecords as any,
      domain: "MACHINE_HEALTH",
    });

    vi.spyOn(apiClient, "getEvidenceRelationships").mockResolvedValue({
      outgoing: mockRelationships as any,
      incoming: [],
    });
    vi.spyOn(apiClient, "getEvidenceProvenance").mockResolvedValue({
      id: "ev-001",
      domain: "MACHINE_HEALTH",
      quality_state: "VERIFIED",
      provenance: { dataset: "NASA-C-MAPSS-FD001" },
    } as any);
    vi.spyOn(apiClient, "getEvidenceBundles").mockResolvedValue(mockBundles as any);
  });

  it("renders workspace title, domain selector, and strict domain notice", async () => {
    render(<EvidencePage />);

    expect(screen.getAllByText("Evidence Intelligence").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("DOMAIN ISOLATION ENFORCED")).toBeDefined();
    expect(screen.getByText(/MACHINE HEALTH \(C-MAPSS\)/i)).toBeDefined();
    expect(screen.getByText(/VISUAL INSPECTION \(MVTec\)/i)).toBeDefined();
  });

  it("loads and displays evidence stream items", async () => {
    render(<EvidencePage />);

    await waitFor(
      () => {
        expect(screen.queryByText(/Loading authoritative evidence records/i)).toBeNull();
      },
      { timeout: 3000 }
    );

    expect(screen.getAllByText("TELEMETRY").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("RUL_PREDICTION").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Telemetry cycle 192/i).length).toBeGreaterThanOrEqual(1);
  });

  it("switches domain to VISUAL_INSPECTION and refreshes evidence stream", async () => {
    vi.spyOn(apiClient, "searchEvidence").mockResolvedValueOnce({
      total: mockEvidenceRecords.length,
      records: mockEvidenceRecords as any,
      domain: "MACHINE_HEALTH",
    }).mockResolvedValueOnce({
      total: mockVisualEvidenceRecords.length,
      records: mockVisualEvidenceRecords as any,
      domain: "VISUAL_INSPECTION",
    });

    render(<EvidencePage />);

    const visualBtn = screen.getByText(/VISUAL INSPECTION \(MVTec\)/i);
    fireEvent.click(visualBtn);

    await waitFor(() => {
      expect(apiClient.searchEvidence).toHaveBeenCalledWith(
        expect.objectContaining({ domain: "VISUAL_INSPECTION" })
      );
    });
  });

  it("selects an evidence record and opens the detail drawer", async () => {
    render(<EvidencePage />);

    await waitFor(() => {
      expect(screen.getAllByText("TELEMETRY").length).toBeGreaterThanOrEqual(1);
    });

    const recordCards = screen.getAllByText("Telemetry cycle 192 recorded for asset TURBOFAN-ENG-001.");
    fireEvent.click(recordCards[0]);

    await waitFor(() => {
      expect(screen.getByText("Structured Payload")).toBeDefined();
      expect(screen.getByText("Causal Graph Relationships")).toBeDefined();
    });
  });

  it("renders bundles browser tab and loads evidence bundles", async () => {
    render(<EvidencePage />);

    const bundlesTab = screen.getByText(/Evidence Bundles/i);
    fireEvent.click(bundlesTab);

    await waitFor(() => {
      expect(apiClient.getEvidenceBundles).toHaveBeenCalled();
      expect(screen.getAllByText("Machine Health Bundle - TURBOFAN-ENG-001").length).toBeGreaterThanOrEqual(1);
    });
  });
});
