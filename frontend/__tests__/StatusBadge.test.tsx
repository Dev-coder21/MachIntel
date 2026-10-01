import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatusBadge } from "@/components/common/StatusBadge";

describe("StatusBadge Component", () => {
  it("renders NORMAL risk state with correct text", () => {
    render(<StatusBadge status="NORMAL" />);
    expect(screen.getByText("NORMAL")).toBeDefined();
  });

  it("renders CRITICAL risk state with custom label", () => {
    render(<StatusBadge status="CRITICAL" label="ALARM HIGH" />);
    expect(screen.getByText("ALARM HIGH")).toBeDefined();
  });

  it("renders ADMIN role badge", () => {
    render(<StatusBadge status="ADMIN" />);
    expect(screen.getByText("ADMIN")).toBeDefined();
  });

  it("renders OPERATOR role badge", () => {
    render(<StatusBadge status="OPERATOR" />);
    expect(screen.getByText("OPERATOR")).toBeDefined();
  });
});
