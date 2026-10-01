import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import PredictionsPage from "@/app/predictions/page";
import { apiClient } from "@/lib/api-client";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/predictions",
}));

describe("PredictionsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders page header and analytical risk disclaimer notice", () => {
    vi.spyOn(apiClient, "getFleetPrognosticsOverview").mockImplementation(() => new Promise(() => {}));
    vi.spyOn(apiClient, "getModels").mockImplementation(() => new Promise(() => {}));
    vi.spyOn(apiClient, "getMachines").mockImplementation(() => new Promise(() => {}));

    render(<PredictionsPage />);
    expect(screen.getByText(/Prognostics & Remaining Useful Life \(RUL\)/i)).toBeDefined();
    expect(screen.getByText(/Analytical Risk Formulation Notice/i)).toBeDefined();
  });

  it("renders model benchmark metrics and fleet health distribution", async () => {
    vi.spyOn(apiClient, "getFleetPrognosticsOverview").mockResolvedValue({
      total_machines: 200,
      machines_with_predictions: 100,
      active_model_id: "rul-randomforest-v1.0.0",
      active_model_algorithm: "RandomForestRegressor",
      average_predicted_rul: 42.5,
      average_health_index: 0.34,
      state_distribution: {
        NORMAL: 25,
        WATCH: 15,
        ELEVATED: 20,
        CRITICAL: 40,
      },
    });

    vi.spyOn(apiClient, "getModels").mockResolvedValue({
      total: 2,
      active_model_id: "rul-randomforest-v1.0.0",
      items: [
        {
          id: "m-1",
          model_id: "rul-randomforest-v1.0.0",
          model_name: "C-MAPSS RUL Random Forest",
          algorithm: "RandomForestRegressor",
          task: "RUL_REGRESSION",
          dataset_identifier: "NASA-C-MAPSS-FD001",
          feature_engineering_version: "1.0.0",
          preprocessing_version: "1.0.0",
          window_size: 20,
          hyperparameters: {},
          metrics: {
            val_rmse: 19.54,
            val_phm_score: 60055.97,
            test_rmse: 19.02,
            test_phm_score: 1306.84,
            train_samples: 16138,
            val_samples: 4493,
            test_samples: 100,
          },
          artifact_path: "/storage/models/rul/rul-randomforest-v1.0.0",
          is_active: true,
          created_at: "2026-10-01T00:00:00Z",
        },
        {
          id: "m-2",
          model_id: "rul-ridge-v1.0.0",
          model_name: "C-MAPSS RUL Ridge",
          algorithm: "Ridge",
          task: "RUL_REGRESSION",
          dataset_identifier: "NASA-C-MAPSS-FD001",
          feature_engineering_version: "1.0.0",
          preprocessing_version: "1.0.0",
          window_size: 20,
          hyperparameters: {},
          metrics: {
            val_rmse: 20.14,
            val_phm_score: 76002.51,
            test_rmse: 18.83,
            test_phm_score: 781.21,
            train_samples: 16138,
            val_samples: 4493,
            test_samples: 100,
          },
          artifact_path: "/storage/models/rul/rul-ridge-v1.0.0",
          is_active: false,
          created_at: "2026-10-01T00:00:00Z",
        },
      ],
    });

    vi.spyOn(apiClient, "getMachines").mockResolvedValue({
      total: 1,
      skip: 0,
      limit: 10,
      items: [
        {
          id: "m-uuid-1",
          machine_id: "TURBOFAN-ENG-001",
          name: "Engine 1",
          machine_type: "TURBOFAN_ENGINE",
          source_dataset: "NASA C-MAPSS (FD001)",
          source_entity_id: "1",
          status: "OPERATIONAL",
          split_category: "INTERNAL_TRAIN",
          total_cycles: 192,
          max_cycle: 192,
          ground_truth_rul: null,
          metadata_json: {},
          created_at: "2026-10-01T00:00:00Z",
          updated_at: "2026-10-01T00:00:00Z",
        },
      ],
    });

    vi.spyOn(apiClient, "getMachineLatestPrediction").mockResolvedValue({
      id: "pred-uuid-1",
      machine_id: "m-uuid-1",
      machine_name: "TURBOFAN-ENG-001",
      model_version: "rul-randomforest-v1.0.0",
      dataset_version: "NASA-C-MAPSS-FD001",
      feature_version: "1.0.0",
      observation_cycle: 192,
      predicted_rul: 1.3,
      health_index: 0.01,
      operational_state: "CRITICAL",
      created_at: "2026-10-01T00:00:00Z",
      metadata_json: {},
    });

    render(<PredictionsPage />);

    await waitFor(() => {
      expect(screen.getAllByText("rul-randomforest-v1.0.0").length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/ACTIVE SERVING/i)).toBeDefined();
      expect(screen.getByText("NORMAL (HI ≥ 0.70)")).toBeDefined();
      expect(screen.getByText("1.3 cyc")).toBeDefined();
    });
  });
});
