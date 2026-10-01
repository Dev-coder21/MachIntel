import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { EmptyState } from "@/components/common/EmptyState";

describe("EmptyState Component", () => {
  it("renders title, description and metadata tag", () => {
    render(
      <EmptyState
        title="No Telemetry Streams"
        description="Connect sensors to view live data"
        metadataTag="GATE: PHASE 2"
      />
    );

    expect(screen.getByText("No Telemetry Streams")).toBeDefined();
    expect(screen.getByText("Connect sensors to view live data")).toBeDefined();
    expect(screen.getByText("GATE: PHASE 2")).toBeDefined();
  });

  it("handles action click event", () => {
    const handleAction = vi.fn();
    render(
      <EmptyState
        title="Empty Actionable State"
        description="Requires operator intervention"
        actionText="Initialize Pipeline"
        onAction={handleAction}
      />
    );

    const button = screen.getByText("Initialize Pipeline");
    expect(button).toBeDefined();
    fireEvent.click(button);
    expect(handleAction).toHaveBeenCalledTimes(1);
  });
});
