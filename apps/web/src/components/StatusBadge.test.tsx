import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { StatusBadge } from "./StatusBadge";

test("formats governance status labels", () => {
  render(<StatusBadge value="require_approval" />);
  expect(screen.getByText("require approval")).toBeInTheDocument();
});
