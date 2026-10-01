import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import MachinesPage from "@/app/machines/page";
import { apiClient, ApiClientError } from "@/lib/api-client";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/machines",
}));

describe("MachinesPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading state initially while fetching machines", () => {
    // Hang the promise
    vi.spyOn(apiClient, "getMachines").mockImplementation(
      () => new Promise(() => {})
    );

    render(<MachinesPage />);
    expect(screen.getByText(/QUERYING POSTGRESQL MACHINE REGISTRY/i)).toBeDefined();
  });

  it("renders real machine list when API returns machines", async () => {
    vi.spyOn(apiClient, "getMachines").mockResolvedValue({
      items: [
        {
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
        },
      ],
      total: 1,
      skip: 0,
      limit: 20,
    });

    render(<MachinesPage />);

    await waitFor(() => {
      expect(screen.getByText("TURBOFAN-ENG-001")).toBeDefined();
      expect(screen.getByText("192 cycles")).toBeDefined();
      expect(screen.getByText("INTERNAL TRAIN")).toBeDefined();
      expect(screen.getByText("INVESTIGATE")).toBeDefined();
    });
  });

  it("renders empty state when zero machines match query", async () => {
    vi.spyOn(apiClient, "getMachines").mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 20,
    });

    render(<MachinesPage />);

    await waitFor(() => {
      expect(screen.getByText("No Machines Found")).toBeDefined();
    });
  });

  it("renders error state when API fails", async () => {
    vi.spyOn(apiClient, "getMachines").mockRejectedValue(
      new ApiClientError("Database connection refused", "DB_ERROR", 500)
    );

    render(<MachinesPage />);

    await waitFor(() => {
      expect(screen.getByText(/Error: Database connection refused/i)).toBeDefined();
      expect(screen.getByText("RETRY")).toBeDefined();
    });
  });
});
