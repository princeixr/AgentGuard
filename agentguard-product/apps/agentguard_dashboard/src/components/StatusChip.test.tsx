import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusChip } from "./StatusChip";

describe("StatusChip", () => {
  it("uses the shared semantic treatment for decisions", () => {
    render(<StatusChip value="require_approval" />);
    expect(screen.getByText("require approval")).toHaveClass(
      "status-chip",
      "status-approval",
    );
  });
});
