import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import MachineDetailPage from "@/app/machines/[id]/page";
import { apiClient } from "@/lib/api-client";
import { MachineDetail } from "@/types/machine";
import {
  CorrelationMatrixResponse,
  FeaturePreviewResponse,
  MachineAnalyticsSummary,
  MachineComparisonResponse,
  SensorTrendResponse,
} from "@/types/analytics";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/machines/TURBOFAN-ENG-001",
}));

describe("MachineDetailPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(React, "use").mockReturnValue({ id: "TURBOFAN-ENG-001" });
  });

  const mockMachineDetail: MachineDetail = {
    id: "m-uuid-1",
    machine_id: "TURBOFAN-ENG-001",
    name: "C-MAPSS Turbofan Engine #1",
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
    active_sensor_channels: ["sensor_2", "sensor_3", "sensor_4"],
    invariant_sensor_channels: ["sensor_1", "sensor_5"],
    quality_issues_count: 7,
  };

  const mockSummary: MachineAnalyticsSummary = {
    machine_id: "TURBOFAN-ENG-001",
    machine_name: "C-MAPSS Turbofan Engine #1",
    source_dataset: "NASA C-MAPSS (FD001)",
    source_entity_id: "1",
    split_category: "INTERNAL_TRAIN",
    status: "OPERATIONAL",
    first_cycle: 1,
    latest_cycle: 192,
    total_cycles: 192,
    active_sensor_count: 15,
    invariant_sensor_count: 7,
    top_drifting_sensors: [
      {
        sensor_key: "sensor_2",
        channel_name: "Total Temperature at LPC Outlet (T24)",
        engineering_unit: "°R",
        min_value: 641.82,
        max_value: 644.53,
        mean_value: 642.68,
        std_value: 0.50,
        initial_value: 641.82,
        latest_value: 644.21,
        net_change: 2.39,
        pct_change: 0.37,
        direction: "STABLE",
      },
    ],
    sensors: [
      {
        sensor_key: "sensor_2",
        channel_name: "Total Temperature at LPC Outlet (T24)",
        engineering_unit: "°R",
        min_value: 641.82,
        max_value: 644.53,
        mean_value: 642.68,
        std_value: 0.50,
        initial_value: 641.82,
        latest_value: 644.21,
        net_change: 2.39,
        pct_change: 0.37,
        direction: "STABLE",
      },
      {
        sensor_key: "sensor_3",
        channel_name: "Total Temperature at HPC Outlet (T30)",
        engineering_unit: "°R",
        min_value: 1582.79,
        max_value: 1605.44,
        mean_value: 1590.52,
        std_value: 6.13,
        initial_value: 1589.70,
        latest_value: 1605.44,
        net_change: 15.74,
        pct_change: 0.99,
        direction: "INCREASING",
      },
    ],
  };

  const mockTrends: SensorTrendResponse = {
    machine_id: "TURBOFAN-ENG-001",
    sensor_key: "sensor_2",
    channel_name: "Total Temperature at LPC Outlet",
    engineering_unit: "°R",
    window_size: 20,
    total_cycles: 192,
    returned_points: 3,
    is_downsampled: false,
    direction: "INCREASING",
    overall_slope: 0.0125,
    points: [
      {
        cycle: 1,
        raw_value: 641.82,
        rolling_mean: 641.82,
        rolling_std: 0.0,
        rolling_min: 641.82,
        rolling_max: 641.82,
        rolling_slope: 0.0,
      },
      {
        cycle: 2,
        raw_value: 642.15,
        rolling_mean: 641.98,
        rolling_std: 0.23,
        rolling_min: 641.82,
        rolling_max: 642.15,
        rolling_slope: 0.33,
      },
      {
        cycle: 3,
        raw_value: 642.35,
        rolling_mean: 642.11,
        rolling_std: 0.27,
        rolling_min: 641.82,
        rolling_max: 642.35,
        rolling_slope: 0.265,
      },
    ],
  };

  const mockCorrelation: CorrelationMatrixResponse = {
    machine_id: "TURBOFAN-ENG-001",
    channels: ["sensor_2", "sensor_3"],
    channel_names: ["LPC Outlet Temp (T24)", "HPC Outlet Temp (T30)"],
    matrix: [
      [1.0, 0.78],
      [0.78, 1.0],
    ],
  };

  const mockFeatures: FeaturePreviewResponse = {
    machine_id: "TURBOFAN-ENG-001",
    feature_engineering_version: "1.0.0",
    window_size: 20,
    min_periods: 1,
    scaling_policy: "Fit strictly on INTERNAL_TRAIN (Units 1-80) during M4",
    total_feature_count: 96,
    columns: [
      { name: "sensor_2_raw", source_channel: "sensor_2", feature_type: "RAW", window: 1 },
      { name: "sensor_2_rolling_mean_w20", source_channel: "sensor_2", feature_type: "ROLLING_MEAN", window: 20 },
    ],
    rows: [
      {
        cycle: 1,
        features: {
          sensor_2_raw: 641.82,
          sensor_2_rolling_mean_w20: 641.82,
          sensor_2_rolling_std_w20: 0.0,
          sensor_2_rolling_slope_w20: 0.0,
        },
      },
    ],
    disclaimer: "DERIVED ANALYTICAL FEATURES ONLY. No ML predictions, Health Index, or RUL estimations.",
  };

  const mockComparison: MachineComparisonResponse = {
    compared_count: 2,
    machines: [
      {
        machine_id: "TURBOFAN-ENG-001",
        source_entity_id: "1",
        split_category: "INTERNAL_TRAIN",
        status: "OPERATIONAL",
        total_cycles: 192,
        max_cycle: 192,
        ground_truth_rul: null,
        drift_t24: 2.39,
        drift_t30: 15.74,
        drift_t50: 12.11,
        drift_p30: -3.45,
        drift_nf: -1.22,
        volatility_score: 0.42,
      },
      {
        machine_id: "TURBOFAN-ENG-002",
        source_entity_id: "2",
        split_category: "INTERNAL_TRAIN",
        status: "OPERATIONAL",
        total_cycles: 287,
        max_cycle: 287,
        ground_truth_rul: null,
        drift_t24: 3.12,
        drift_t30: 18.95,
        drift_t50: 14.50,
        drift_p30: -4.10,
        drift_nf: -1.80,
        volatility_score: 0.48,
      },
    ],
  };

  it("renders machine analytics overview and rolling trend stream", async () => {
    vi.spyOn(apiClient, "getMachine").mockResolvedValue(mockMachineDetail);
    vi.spyOn(apiClient, "getMachineAnalyticsSummary").mockResolvedValue(mockSummary);
    vi.spyOn(apiClient, "getMachineSensorTrends").mockResolvedValue(mockTrends);
    vi.spyOn(apiClient, "getMachineCorrelation").mockResolvedValue(mockCorrelation);
    vi.spyOn(apiClient, "getMachineFeaturePreview").mockResolvedValue(mockFeatures);

    render(
      <React.Suspense fallback={<div>Loading...</div>}>
        <MachineDetailPage params={Promise.resolve({ id: "TURBOFAN-ENG-001" })} />
      </React.Suspense>
    );

    await waitFor(() => {
      expect(screen.getByText(/Asset Analytics: TURBOFAN-ENG-001/i)).toBeDefined();
      expect(screen.getByText("192 Cycles Recorded")).toBeDefined();
      expect(screen.getByText("DUAL OVERLAY")).toBeDefined();
      expect(screen.getByText("TEMPORALLY CAUSAL (NO FUTURE LOOKAHEAD)")).toBeDefined();
    });
  });

  it("navigates to Sensor Statistics Matrix tab", async () => {
    vi.spyOn(apiClient, "getMachine").mockResolvedValue(mockMachineDetail);
    vi.spyOn(apiClient, "getMachineAnalyticsSummary").mockResolvedValue(mockSummary);
    vi.spyOn(apiClient, "getMachineSensorTrends").mockResolvedValue(mockTrends);
    vi.spyOn(apiClient, "getMachineCorrelation").mockResolvedValue(mockCorrelation);
    vi.spyOn(apiClient, "getMachineFeaturePreview").mockResolvedValue(mockFeatures);

    render(
      <React.Suspense fallback={<div>Loading...</div>}>
        <MachineDetailPage params={Promise.resolve({ id: "TURBOFAN-ENG-001" })} />
      </React.Suspense>
    );

    await waitFor(() => {
      expect(screen.getByText("SENSOR STATISTICS MATRIX")).toBeDefined();
    });

    fireEvent.click(screen.getByText("SENSOR STATISTICS MATRIX"));

    await waitFor(() => {
      expect(screen.getByText("CHANNEL KEY")).toBeDefined();
      expect(screen.getByText("sensor_2")).toBeDefined();
      expect(screen.getByText("sensor_3")).toBeDefined();
    });
  });

  it("navigates to ML Feature Preview tab and displays disclaimer", async () => {
    vi.spyOn(apiClient, "getMachine").mockResolvedValue(mockMachineDetail);
    vi.spyOn(apiClient, "getMachineAnalyticsSummary").mockResolvedValue(mockSummary);
    vi.spyOn(apiClient, "getMachineSensorTrends").mockResolvedValue(mockTrends);
    vi.spyOn(apiClient, "getMachineCorrelation").mockResolvedValue(mockCorrelation);
    vi.spyOn(apiClient, "getMachineFeaturePreview").mockResolvedValue(mockFeatures);

    render(
      <React.Suspense fallback={<div>Loading...</div>}>
        <MachineDetailPage params={Promise.resolve({ id: "TURBOFAN-ENG-001" })} />
      </React.Suspense>
    );

    await waitFor(() => {
      expect(screen.getByText("ML FEATURE PREVIEW")).toBeDefined();
    });

    fireEvent.click(screen.getByText("ML FEATURE PREVIEW"));

    await waitFor(() => {
      expect(screen.getByText(/PHASE 4 ML HANDOFF CONTRACT/i)).toBeDefined();
      expect(screen.getByText(/DERIVED ANALYTICAL FEATURES ONLY/i)).toBeDefined();
    });
  });

  it("navigates to Asset Comparison tab", async () => {
    vi.spyOn(apiClient, "getMachine").mockResolvedValue(mockMachineDetail);
    vi.spyOn(apiClient, "getMachineAnalyticsSummary").mockResolvedValue(mockSummary);
    vi.spyOn(apiClient, "getMachineSensorTrends").mockResolvedValue(mockTrends);
    vi.spyOn(apiClient, "getMachineCorrelation").mockResolvedValue(mockCorrelation);
    vi.spyOn(apiClient, "getMachineFeaturePreview").mockResolvedValue(mockFeatures);
    vi.spyOn(apiClient, "compareMachines").mockResolvedValue(mockComparison);

    render(
      <React.Suspense fallback={<div>Loading...</div>}>
        <MachineDetailPage params={Promise.resolve({ id: "TURBOFAN-ENG-001" })} />
      </React.Suspense>
    );

    await waitFor(() => {
      expect(screen.getByText("ASSET COMPARISON")).toBeDefined();
    });

    fireEvent.click(screen.getByText("ASSET COMPARISON"));

    await waitFor(() => {
      expect(screen.getByText("COMPARE WITH ASSET:")).toBeDefined();
      expect(screen.getByText("Mean Thermal Volatility (σ)")).toBeDefined();
    });
  });
});
