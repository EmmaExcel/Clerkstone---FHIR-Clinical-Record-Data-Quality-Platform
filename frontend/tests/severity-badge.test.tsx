import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { SeverityBadge } from "@/components/ui/SeverityBadge";

describe("SeverityBadge", () => {
  it("renders the severity as a text label, not colour alone", () => {
    render(<SeverityBadge severity="error" />);
    expect(screen.getByText("Error")).toBeInTheDocument();
  });

  it("renders warning and info labels", () => {
    render(
      <>
        <SeverityBadge severity="warning" />
        <SeverityBadge severity="info" />
      </>,
    );
    expect(screen.getByText("Warning")).toBeInTheDocument();
    expect(screen.getByText("Info")).toBeInTheDocument();
  });

  it("keeps the decorative icon hidden from the accessibility tree", () => {
    const { container } = render(<SeverityBadge severity="error" />);
    const icon = container.querySelector("svg");
    expect(icon).toBeInTheDocument();
    expect(icon).toHaveAttribute("aria-hidden", "true");
  });
});
