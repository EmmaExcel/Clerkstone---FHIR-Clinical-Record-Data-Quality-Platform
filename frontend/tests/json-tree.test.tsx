import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { JsonTree } from "@/components/resource-viewer/JsonTree";

describe("JsonTree", () => {
  it("pretty-prints a resource", () => {
    const { container } = render(<JsonTree data={{ resourceType: "Encounter" }} highlighted={new Set()} />);
    expect(container.textContent).toContain("resourceType");
    expect(container.textContent).toContain("Encounter");
  });

  it("flags a matched node with screen-reader text, not colour alone", () => {
    const data = { period: { end: "2026-08-30T10:00:00Z" } };
    render(<JsonTree data={data} highlighted={new Set(["/period/end"])} />);
    expect(screen.getByText(/matches FHIRPath expression/i)).toBeInTheDocument();
  });
});
