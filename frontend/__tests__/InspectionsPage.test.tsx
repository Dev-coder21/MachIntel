import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import InspectionsPage from "@/app/inspections/page";
import { apiClient } from "@/lib/api-client";
import * as authContext from "@/lib/auth-context";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/inspections",
}));

const mockRuns = [
  {
    id: "run-001",
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
        confusion_matrix: {
          true_negative: 21,
          false_positive: 1,
          false_negative: 6,
          true_positive: 87,
        },
      },
      pixel_level_metrics: {
        pixel_roc_auc: 0.9769,
        mask_evaluated_images: 93,
      },
      defect_breakdown: {
        bent: { total_images: 25, passed_count: 1, defect_count: 24, accuracy: 0.96, mean_score: 3.51, min_score: 2.72, max_score: 4.16 },
        color: { total_images: 22, passed_count: 1, defect_count: 21, accuracy: 0.955, mean_score: 3.48, min_score: 2.6, max_score: 4.05 },
        flip: { total_images: 23, passed_count: 0, defect_count: 23, accuracy: 1.0, mean_score: 3.77, min_score: 3.6, max_score: 4.04 },
        good: { total_images: 22, passed_count: 21, defect_count: 1, accuracy: 0.955, mean_score: 2.54, min_score: 2.33, max_score: 2.84 },
        scratch: { total_images: 23, passed_count: 4, defect_count: 19, accuracy: 0.826, mean_score: 3.28, min_score: 2.64, max_score: 3.76 },
      },
    },
    created_at: "2026-10-01T05:21:00Z",
  },
];

const mockSummary = {
  run_id: "run-001",
  dataset_identifier: "MVTec-AD-metal_nut",
  category: "metal_nut",
  model_version: "mvtec-patchcore-metalnut-v1.0.0",
  policy_version: "cv-policy-v1.0.0",
  threshold: 2.8155,
  total_images: 115,
  passed_count: 22,
  defect_count: 93,
  defect_rate: 0.8087,
  metrics: {
    roc_auc: 0.9858,
    pr_auc: 0.9967,
    precision: 0.9886,
    recall: 0.9355,
    f1_score: 0.9613,
    confusion_matrix: {
      true_negative: 21,
      false_positive: 1,
      false_negative: 6,
      true_positive: 87,
    },
  },
  defect_breakdown: {
    bent: { total_images: 25, passed_count: 1, defect_count: 24, accuracy: 0.96, mean_score: 3.51, min_score: 2.72, max_score: 4.16 },
    good: { total_images: 22, passed_count: 21, defect_count: 1, accuracy: 0.955, mean_score: 2.54, min_score: 2.33, max_score: 2.84 },
  },
};

const mockResults = [
  {
    id: "res-001",
    run_id: "run-001",
    split: "test",
    defect_class: "bent",
    source_image_filename: "000.png",
    image_level_score: 3.513,
    decision: "DEFECT" as const,
    ground_truth_label: "DEFECT" as const,
    has_heatmap: true,
    has_overlay: true,
    has_ground_truth_mask: true,
    inference_metadata: {
      model_version: "mvtec-patchcore-metalnut-v1.0.0",
      backbone: "wide_resnet50_2",
      inference_time_ms: 38.5,
    },
    created_at: "2026-10-01T05:21:05Z",
  },
  {
    id: "res-002",
    run_id: "run-001",
    split: "test",
    defect_class: "good",
    source_image_filename: "001.png",
    image_level_score: 2.538,
    decision: "PASS" as const,
    ground_truth_label: "PASS" as const,
    has_heatmap: true,
    has_overlay: true,
    has_ground_truth_mask: false,
    inference_metadata: {
      model_version: "mvtec-patchcore-metalnut-v1.0.0",
      backbone: "wide_resnet50_2",
      inference_time_ms: 36.2,
    },
    created_at: "2026-10-01T05:21:06Z",
  },
];

describe("InspectionsPage", () => {
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

    vi.spyOn(apiClient, "getInspectionRuns").mockResolvedValue(mockRuns);
    vi.spyOn(apiClient, "getInspectionRun").mockResolvedValue(mockRuns[0]);
    vi.spyOn(apiClient, "getInspectionSummary").mockResolvedValue(mockSummary);
    vi.spyOn(apiClient, "getInspectionResults").mockResolvedValue(mockResults);
    vi.spyOn(apiClient, "getInspectionArtifactUrl").mockImplementation(
      (id, type) => `http://localhost:8000/api/v1/inspections/results/${id}/${type}`
    );
  });

  it("renders page header and provenance metadata", async () => {
    render(<InspectionsPage />);

    expect(screen.getByText("Visual Inspection Command Station")).toBeDefined();
    await waitFor(() => {
      expect(screen.getByText("PatchCore-v1")).toBeDefined();
      expect(screen.getByText("WideResNet-50-2 (layer2+3)")).toBeDefined();
      expect(screen.getByText("MVTec AD")).toBeDefined();
    });
  });

  it("renders inspection run summary KPIs and benchmark breakdown", async () => {
    render(<InspectionsPage />);

    await waitFor(() => {
      expect(screen.getByText("115")).toBeDefined();
      expect(screen.getByText("93")).toBeDefined();
      expect(screen.getByText("22")).toBeDefined();
      expect(screen.getByText("98.6%")).toBeDefined();
      expect(screen.getByText("97.7%")).toBeDefined();
    });
  });

  it("renders result cards with model decision and benchmark ground truth", async () => {
    render(<InspectionsPage />);

    await waitFor(() => {
      expect(screen.getByText("000.png")).toBeDefined();
      expect(screen.getByText("001.png")).toBeDefined();
      expect(screen.getByText("GT: BENT")).toBeDefined();
      expect(screen.getByText("GT: GOOD")).toBeDefined();
    });
  });

  it("opens modal detail workspace when a result card is clicked", async () => {
    render(<InspectionsPage />);

    await waitFor(() => {
      expect(screen.getByText("000.png")).toBeDefined();
    });

    fireEvent.click(screen.getByText("000.png"));

    await waitFor(() => {
      expect(screen.getByText("MODEL DECISION: DEFECT")).toBeDefined();
      expect(screen.getByText("Localization Overlay")).toBeDefined();
      expect(screen.getByText("Anomaly Heatmap")).toBeDefined();
      expect(screen.getByText("Raw Capture")).toBeDefined();
      expect(screen.getByText("GT Mask")).toBeDefined();
    });
  });

  it("allows switching view mode tabs in modal", async () => {
    render(<InspectionsPage />);

    await waitFor(() => {
      expect(screen.getByText("000.png")).toBeDefined();
    });

    fireEvent.click(screen.getByText("000.png"));

    await waitFor(() => {
      expect(screen.getByText("Anomaly Heatmap")).toBeDefined();
    });

    fireEvent.click(screen.getByText("Anomaly Heatmap"));
    expect(screen.getByText("View: HEATMAP (224x224)")).toBeDefined();
  });

  it("filters results when clicking defect class pill", async () => {
    render(<InspectionsPage />);

    await waitFor(() => {
      expect(screen.getByText("BENT")).toBeDefined();
    });

    fireEvent.click(screen.getByText("BENT"));

    await waitFor(() => {
      expect(apiClient.getInspectionResults).toHaveBeenCalledWith(
        "run-001",
        expect.objectContaining({ defect_class: "bent" })
      );
    });
  });
});
