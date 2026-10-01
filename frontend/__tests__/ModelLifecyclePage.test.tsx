import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ModelLifecyclePage from "@/app/admin/models/page";
import { apiClient } from "@/lib/api-client";
import * as authContext from "@/lib/auth-context";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/admin/models",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => ({ get: vi.fn().mockReturnValue(null) }),
}));

describe("ModelLifecyclePage (M14 MLOps & Model Governance)", () => {
  const mockModels = [
    {
      id: "mod-1",
      model_id: "rul-randomforest-v1.0.0",
      model_name: "C-MAPSS RUL Random Forest Regressor",
      domain: "MACHINE_HEALTH",
      model_family: "RUL_REGRESSION",
      algorithm: "RandomForestRegressor",
      task: "RUL_REGRESSION",
      version: "1.0.0",
      status: "PROMOTED",
      framework: "scikit-learn",
      dataset_identifier: "NASA-C-MAPSS-FD001",
      feature_engineering_version: "1.0.0",
      preprocessing_version: "1.0.0",
      window_size: 20,
      hyperparameters: { n_estimators: 100, max_depth: 12 },
      metrics: { val_rmse: 19.5411, test_rmse: 19.0187 },
      artifact_path: "storage/models/rul/rul-randomforest-v1.0.0",
      artifact_sha256: "186cda72751d0cfbe3408968b6682e65b993d7fd972646bce0c914e999571b1b",
      artifact_size_bytes: 17435969,
      training_manifest: { dataset: "NASA C-MAPSS FD001" },
      is_active: true,
      created_at: "2026-10-01T00:00:00Z",
    },
    {
      id: "mod-2",
      model_id: "mvtec-patchcore-metalnut-v1.0.0",
      model_name: "PatchCore Metal Nut Visual Inspection Model",
      domain: "VISUAL_INSPECTION",
      model_family: "ANOMALY_DETECTION",
      algorithm: "PatchCore-WideResNet50",
      task: "VISUAL_ANOMALY_DETECTION",
      version: "1.0.0",
      status: "PROMOTED",
      framework: "pytorch",
      dataset_identifier: "MVTec-AD-metal_nut",
      feature_engineering_version: "cv-feature-config-v1.0.0",
      preprocessing_version: "1.0.0",
      window_size: 0,
      hyperparameters: { backbone: "wide_resnet50_2", threshold: 2.8155 },
      metrics: { roc_auc: 0.9858, f1_score: 0.9613 },
      artifact_path: "storage/models/cv/mvtec-patchcore-metalnut-v1.0.0",
      artifact_sha256: "e63181c3b44a541861a30b375800e08169fcd7fd0205f464ad3596fe21f60d90",
      artifact_size_bytes: 52987461,
      training_manifest: { dataset: "MVTec AD metal_nut" },
      is_active: true,
      created_at: "2026-10-01T00:00:00Z",
    },
  ];

  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.setItem("user", JSON.stringify({ username: "admin", role: "ADMIN" }));

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

    vi.spyOn(apiClient, "getModels").mockResolvedValue({
      total: 2,
      active_machine_health_model_id: "rul-randomforest-v1.0.0",
      active_visual_inspection_model_id: "mvtec-patchcore-metalnut-v1.0.0",
      active_model_id: "rul-randomforest-v1.0.0",
      items: mockModels as any,
    });

    vi.spyOn(apiClient, "getModel").mockResolvedValue(mockModels[0] as any);

    vi.spyOn(apiClient, "getModelEvaluations").mockResolvedValue([
      {
        id: "eval-1",
        model_version_id: "mod-1",
        evaluation_type: "VALIDATION_AND_TEST_BENCHMARK",
        dataset_identifier: "NASA-C-MAPSS-FD001",
        split: "official_test",
        metrics: { val_rmse: 19.5411, test_rmse: 19.0187 },
        manifest: {},
        gate_result: "PASSED",
        gate_details: {},
        evaluator: "m4-evaluation-harness",
        evaluated_at: "2026-10-01T12:00:00Z",
        created_at: "2026-10-01T12:00:00Z",
      },
    ]);

    vi.spyOn(apiClient, "getModelPromotions").mockResolvedValue([]);

    vi.spyOn(apiClient, "getModelIntegrity").mockResolvedValue({
      model_id: "rul-randomforest-v1.0.0",
      domain: "MACHINE_HEALTH",
      status: "PROMOTED",
      artifact_path: "storage/models/rul/rul-randomforest-v1.0.0",
      is_valid: true,
      expected_sha256: "186cda72751d0cfbe3408968b6682e65b993d7fd972646bce0c914e999571b1b",
      computed_sha256: "186cda72751d0cfbe3408968b6682e65b993d7fd972646bce0c914e999571b1b",
      file_size_bytes: 17435969,
      verified_at: "2026-10-01T12:00:00Z",
      details: {},
    });

    vi.spyOn(apiClient, "verifyModelIntegrity").mockResolvedValue({
      model_id: "rul-randomforest-v1.0.0",
      domain: "MACHINE_HEALTH",
      status: "PROMOTED",
      artifact_path: "storage/models/rul/rul-randomforest-v1.0.0",
      is_valid: true,
      expected_sha256: "186cda72751d0cfbe3408968b6682e65b993d7fd972646bce0c914e999571b1b",
      computed_sha256: "186cda72751d0cfbe3408968b6682e65b993d7fd972646bce0c914e999571b1b",
      file_size_bytes: 17435969,
      verified_at: "2026-10-01T12:00:00Z",
      details: {},
    });

    vi.spyOn(apiClient, "getModelGates").mockResolvedValue({
      can_promote: true,
      model_id: "rul-randomforest-v1.0.0",
      domain: "MACHINE_HEALTH",
      policy_version: "policy-v1.0.0",
      passed_gates: [
        "GATE_1_ARTIFACT_EXISTS",
        "GATE_2_CHECKSUM_VALID",
        "GATE_3_DATASET_VALID",
        "GATE_4_FEATURE_CONFIG_VALID",
        "GATE_5_EVALUATION_MANIFEST_EXISTS",
        "GATE_6_REQUIRED_METRICS_PRESENT",
        "GATE_7_EVALUATION_PASSED",
        "GATE_8_DOMAIN_ROLE_CONSISTENT",
      ],
      failed_gates: [],
      gate_details: {},
    });

    vi.spyOn(apiClient, "getModelMonitoringSummary").mockResolvedValue({
      domain: "MACHINE_HEALTH",
      active_model_id: "rul-randomforest-v1.0.0",
      status: "OPERATIONAL",
      total_inferences: 42,
      last_inference_timestamp: "2026-10-01T12:00:00Z",
      data_classification: "OBSERVED",
      distribution_summary: {},
    });
  });

  it("renders page title and top KPI ribbon with active models", async () => {
    render(<ModelLifecyclePage />);

    expect(screen.getByText(/MODEL LIFECYCLE & REGISTRY/i)).toBeDefined();
    await waitFor(() => {
      expect(screen.getByText("ACTIVE RUL MODEL")).toBeDefined();
      expect(screen.getByText("ACTIVE VISION MODEL")).toBeDefined();
      expect(screen.getByText("REGISTERED ARTIFACTS")).toBeDefined();
      expect(screen.getByText("DETERMINISTIC GATES")).toBeDefined();
    });
  });

  it("renders registered models table with status badges and SHA-256", async () => {
    render(<ModelLifecyclePage />);

    await waitFor(() => {
      expect(screen.getAllByText("rul-randomforest-v1.0.0").length).toBeGreaterThan(0);
      expect(screen.getAllByText("mvtec-patchcore-metalnut-v1.0.0").length).toBeGreaterThan(0);
      expect(screen.getAllByText("PROMOTED").length).toBeGreaterThanOrEqual(2);
      expect(screen.getAllByText("PRODUCTION").length).toBeGreaterThanOrEqual(2);
    });
  });

  it("opens detail drawer with manifests, lineage, and evaluation records on Inspect", async () => {
    render(<ModelLifecyclePage />);

    await waitFor(() => {
      expect(screen.getAllByText("rul-randomforest-v1.0.0").length).toBeGreaterThan(0);
    });

    const inspectButtons = screen.getAllByRole("button", { name: /^Inspect$/ });
    fireEvent.click(inspectButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/DATASET & FEATURE LINEAGE/i)).toBeDefined();
    });
  });

  it("executes cryptographic SHA-256 integrity verification on demand", async () => {
    render(<ModelLifecyclePage />);

    await waitFor(() => {
      expect(screen.getAllByText("rul-randomforest-v1.0.0").length).toBeGreaterThan(0);
    });

    const inspectButtons = screen.getAllByRole("button", { name: /^Inspect$/ });
    fireEvent.click(inspectButtons[0]);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Verify SHA-256/i })).toBeDefined();
    });

    const verifyBtn = screen.getByRole("button", { name: /Verify SHA-256/i });
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(apiClient.verifyModelIntegrity).toHaveBeenCalledWith("rul-randomforest-v1.0.0");
      expect(screen.getByText(/Cryptographic SHA-256 verification PASSED/i)).toBeDefined();
    });
  });

  it("allows domain filtering tabs to trigger filtered requests", async () => {
    render(<ModelLifecyclePage />);

    await waitFor(() => {
      expect(screen.getByText("MACHINE HEALTH (RUL)")).toBeDefined();
    });

    fireEvent.click(screen.getByText("MACHINE HEALTH (RUL)"));

    await waitFor(() => {
      expect(apiClient.getModels).toHaveBeenCalledWith(
        expect.objectContaining({ domain: "MACHINE_HEALTH" })
      );
    });
  });
});
