import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import AnalyticsPage from "@/app/analytics/page";
import { apiClient } from "@/lib/api-client";
import * as authContext from "@/lib/auth-context";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/analytics",
}));

const mockRuns = [
  {
    id: "0b0dbb58-0d06-46fc-a98d-ac617211080c",
    dataset_identifier: "MVTec-AD-metal_nut",
    category: "metal_nut",
    model_version: "mvtec-patchcore-metalnut-v1.0.0",
    feature_config_version: "cv-feature-config-v1.0.0",
    policy_version: "cv-policy-v1.0.0",
    status: "COMPLETED",
    threshold: 2.8155,
    total_images: 115,
    passed_count: 22,
    defect_count: 93,
    evaluation_summary: {
      image_level_metrics: {
        roc_auc: 0.9858,
        pr_auc: 0.9967,
        precision: 0.9886,
        recall: 0.9355,
        f1_score: 0.9613,
      },
      pixel_level_metrics: {
        pixel_roc_auc: 0.9769,
        mask_evaluated_images: 93,
      },
    },
    created_at: "2026-10-01T05:21:00Z",
  },
];

const mockSummary = {
  run_id: "0b0dbb58-0d06-46fc-a98d-ac617211080c",
  dataset_identifier: "MVTec-AD-metal_nut",
  category: "metal_nut",
  model_version: "mvtec-patchcore-metalnut-v1.0.0",
  feature_config_version: "cv-feature-config-v1.0.0",
  policy_version: "cv-policy-v1.0.0",
  status: "COMPLETED",
  threshold: 2.8155,
  total_images: 115,
  passed_count: 22,
  defect_count: 93,
  observed_defect_rate: 0.8087,
  score_min: 2.33,
  score_max: 4.16,
  score_mean: 3.42,
  score_median: 3.51,
  evaluation_metrics: {
    roc_auc: 0.9858,
    f1_score: 0.9613,
  },
  created_at: "2026-10-01T05:21:00Z",
};

const mockScoreDist = {
  run_id: "0b0dbb58-0d06-46fc-a98d-ac617211080c",
  threshold: 2.8155,
  overall_stats: {
    min: 2.33,
    max: 4.16,
    mean: 3.42,
    median: 3.51,
    p25: 3.12,
    p75: 3.75,
    p90: 3.98,
    p95: 4.07,
  },
  normal_stats: {
    min: 2.33,
    max: 2.84,
    mean: 2.54,
    median: 2.52,
    p25: 2.45,
    p75: 2.65,
    p90: 2.76,
    p95: 2.81,
  },
  defective_stats: {
    min: 2.6,
    max: 4.16,
    mean: 3.56,
    median: 3.58,
    p25: 3.35,
    p75: 3.82,
    p90: 4.01,
    p95: 4.08,
  },
  histogram: [
    { bin_start: 2.33, bin_end: 2.45, normal_count: 8, defect_count: 0, total_count: 8 },
    { bin_start: 2.45, bin_end: 2.57, normal_count: 9, defect_count: 0, total_count: 9 },
    { bin_start: 2.57, bin_end: 2.7, normal_count: 4, defect_count: 2, total_count: 6 },
    { bin_start: 2.7, bin_end: 2.82, normal_count: 1, defect_count: 4, total_count: 5 },
    { bin_start: 2.82, bin_end: 2.94, normal_count: 0, defect_count: 6, total_count: 6 },
    { bin_start: 2.94, bin_end: 3.06, normal_count: 0, defect_count: 12, total_count: 12 },
  ],
};

const mockDefectAnalytics = {
  run_id: "0b0dbb58-0d06-46fc-a98d-ac617211080c",
  category: "metal_nut",
  classes: [
    {
      defect_class: "bent",
      image_count: 25,
      detected_count: 24,
      missed_count: 1,
      observed_detection_rate: 0.96,
      mean_score: 3.51,
      min_score: 2.72,
      max_score: 4.16,
    },
    {
      defect_class: "color",
      image_count: 22,
      detected_count: 21,
      missed_count: 1,
      observed_detection_rate: 0.9545,
      mean_score: 3.48,
      min_score: 2.6,
      max_score: 4.05,
    },
    {
      defect_class: "flip",
      image_count: 23,
      detected_count: 23,
      missed_count: 0,
      observed_detection_rate: 1.0,
      mean_score: 3.77,
      min_score: 3.6,
      max_score: 4.04,
    },
    {
      defect_class: "good",
      image_count: 22,
      detected_count: 21,
      missed_count: 1,
      observed_detection_rate: 0.9545,
      mean_score: 2.54,
      min_score: 2.33,
      max_score: 2.84,
    },
    {
      defect_class: "scratch",
      image_count: 23,
      detected_count: 19,
      missed_count: 4,
      observed_detection_rate: 0.8261,
      mean_score: 3.28,
      min_score: 2.64,
      max_score: 3.76,
    },
  ],
};

const mockConfusionMatrix = {
  run_id: "0b0dbb58-0d06-46fc-a98d-ac617211080c",
  true_positives: 87,
  true_negatives: 21,
  false_positives: 1,
  false_negatives: 6,
  precision: 0.9886,
  recall: 0.9355,
  f1_score: 0.9613,
  specificity: 0.9545,
  image_roc_auc: 0.9858,
  image_pr_auc: 0.9967,
  threshold: 2.8155,
};

const mockLocalization = {
  run_id: "0b0dbb58-0d06-46fc-a98d-ac617211080c",
  pixel_roc_auc: 0.9769,
  mask_evaluated_images: 93,
  has_localization: true,
  localization_method: "patchcore_anomaly_map_upsampled",
  resolution: "224x224",
};

const mockProvenance = {
  run_id: "0b0dbb58-0d06-46fc-a98d-ac617211080c",
  dataset_identifier: "MVTec-AD-metal_nut",
  category: "metal_nut",
  model_version: "mvtec-patchcore-metalnut-v1.0.0",
  feature_config_version: "cv-feature-config-v1.0.0",
  policy_version: "cv-policy-v1.0.0",
  threshold: 2.8155,
  normal_training_stats: {
    backbone: "wide_resnet50_2",
    layers: ["layer2", "layer3"],
    coreset_sampling_ratio: 0.1,
    train_images: 220,
    coreset_patches: 1000,
  },
  created_at: "2026-10-01T05:21:00Z",
};

const mockComparison = {
  is_available: false,
  reason: "Comparative analysis requires at least 2 distinct persisted inspection runs. Only 1 run exists in registry.",
  total_runs: 1,
  runs: [
    {
      run_id: "0b0dbb58-0d06-46fc-a98d-ac617211080c",
      model_version: "mvtec-patchcore-metalnut-v1.0.0",
      policy_version: "cv-policy-v1.0.0",
      threshold: 2.8155,
      total_images: 115,
      passed_count: 22,
      defect_count: 93,
      observed_defect_rate: 0.8087,
      roc_auc: 0.9858,
      pr_auc: 0.9967,
      precision: 0.9886,
      recall: 0.9355,
      f1_score: 0.9613,
      pixel_roc_auc: 0.9769,
      created_at: "2026-10-01T05:21:00Z",
    },
  ],
};

describe("InspectionAnalyticsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(authContext, "useAuth").mockReturnValue({
      user: {
        id: "user-1",
        username: "admin",
        email: "admin@machintel.com",
        full_name: "Admin User",
        role: "ADMIN" as any,
        is_active: true,
        created_at: "2026-10-01T00:00:00Z",
        updated_at: "2026-10-01T00:00:00Z",
      },
      token: "mock-token",
      isLoading: false,
      isAuthenticated: true,
      login: vi.fn(),
      logout: vi.fn(),
      refreshUser: vi.fn(),
    });

    vi.spyOn(apiClient, "getInspectionAnalyticsRuns").mockResolvedValue(mockRuns as any);
    vi.spyOn(apiClient, "getInspectionAnalyticsSummary").mockResolvedValue(mockSummary as any);
    vi.spyOn(apiClient, "getInspectionAnalyticsScores").mockResolvedValue(mockScoreDist as any);
    vi.spyOn(apiClient, "getInspectionAnalyticsDefects").mockResolvedValue(mockDefectAnalytics as any);
    vi.spyOn(apiClient, "getInspectionAnalyticsConfusionMatrix").mockResolvedValue(mockConfusionMatrix as any);
    vi.spyOn(apiClient, "getInspectionAnalyticsLocalization").mockResolvedValue(mockLocalization as any);
    vi.spyOn(apiClient, "getInspectionAnalyticsProvenance").mockResolvedValue(mockProvenance as any);
    vi.spyOn(apiClient, "getInspectionAnalyticsComparison").mockResolvedValue(mockComparison as any);
  });

  it("renders page header and provenance details", async () => {
    render(<AnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 1, name: "Inspection Analytics" })).toBeDefined();
      expect(screen.getAllByText(/0b0dbb58/).length).toBeGreaterThan(0);
      expect(screen.getAllByText("mvtec-patchcore-metalnut-v1.0.0").length).toBeGreaterThan(0);
      expect(screen.getAllByText("cv-policy-v1.0.0").length).toBeGreaterThan(0);
    });
  });

  it("renders KPI ribbon with real metrics", async () => {
    render(<AnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText("Evaluated")).toBeDefined();
    });

    expect(screen.getAllByText("115").length).toBeGreaterThan(0);
    expect(screen.getByText("Defect Rate")).toBeDefined();
    expect(screen.getAllByText("80.9%").length).toBeGreaterThan(0);
    expect(screen.getByText("Image ROC-AUC")).toBeDefined();
    expect(screen.getAllByText("98.6%").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Pixel ROC-AUC").length).toBeGreaterThan(0);
    expect(screen.getAllByText("97.7%").length).toBeGreaterThan(0);
  });

  it("renders score distribution and threshold marker", async () => {
    render(<AnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText(/ANOMALY SCORE DISTRIBUTION/)).toBeDefined();
    });

    // Check threshold badge
    expect(screen.getAllByText(/2\.8155/).length).toBeGreaterThan(0);
    expect(screen.getByText("Normal Distribution (Test)")).toBeDefined();
    expect(screen.getByText("Defective Distribution (Test)")).toBeDefined();
    expect(screen.getByText("Separation Margin (Delta)")).toBeDefined();
  });

  it("renders confusion matrix with accurate values", async () => {
    render(<AnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText(/CONFUSION MATRIX & METRICS/)).toBeDefined();
    });

    expect(screen.getAllByText("87").length).toBeGreaterThan(0); // TP
    expect(screen.getAllByText("21").length).toBeGreaterThan(0); // TN
    expect(screen.getAllByText("1").length).toBeGreaterThan(0);  // FP
    expect(screen.getAllByText("6").length).toBeGreaterThan(0);  // FN
    expect(screen.getAllByText("98.9%").length).toBeGreaterThan(0); // Precision
    expect(screen.getAllByText("93.5%").length).toBeGreaterThan(0); // Recall
    expect(screen.getAllByText("96.1%").length).toBeGreaterThan(0); // F1
    expect(screen.getAllByText("95.5%").length).toBeGreaterThan(0); // Specificity
  });

  it("renders defect category breakdown table", async () => {
    render(<AnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText(/DEFECT CATEGORY DETECTION PERFORMANCE/)).toBeDefined();
    });

    expect(screen.getAllByText("bent").length).toBeGreaterThan(0);
    expect(screen.getAllByText("color").length).toBeGreaterThan(0);
    expect(screen.getAllByText("flip").length).toBeGreaterThan(0);
    expect(screen.getAllByText("scratch").length).toBeGreaterThan(0);
    expect(screen.getAllByText("good").length).toBeGreaterThan(0);
  });

  it("renders localization analytics details", async () => {
    render(<AnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText(/PIXEL-LEVEL DEFECT LOCALIZATION PERFORMANCE/)).toBeDefined();
    });

    expect(screen.getAllByText(/93 Masks/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("patchcore_anomaly_map_upsampled").length).toBeGreaterThan(0);
  });

  it("renders model comparison unavailable state when single run exists", async () => {
    render(<AnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText("INSUFFICIENT COMPARISON RUNS")).toBeDefined();
    });

    expect(
      screen.getByText(
        /Comparative analysis requires at least 2 distinct persisted inspection runs/
      )
    ).toBeDefined();
  });

  it("renders empty state when no runs are returned", async () => {
    vi.spyOn(apiClient, "getInspectionAnalyticsRuns").mockResolvedValue([]);
    render(<AnalyticsPage />);

    await waitFor(() => {
      expect(screen.getByText("No Inspection Runs Available")).toBeDefined();
    });
  });
});
