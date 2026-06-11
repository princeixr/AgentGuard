import type { Decision } from "../api/types";

export function StatusChip({
  value,
  label,
}: {
  value: Decision | string;
  label?: string;
}) {
  const normalized = value.toLowerCase();
  const tone =
    normalized === "approved"
      ? "approved"
      : normalized === "allow" || normalized === "allowed"
      ? "allow"
      : normalized === "block" ||
          normalized === "blocked" ||
          normalized === "rejected"
        ? "block"
        : normalized.includes("approval") || normalized === "pending"
          ? "approval"
          : normalized === "warn"
            ? "warn"
            : normalized === "review"
              ? "review"
              : "neutral";

  return (
    <span className={`status-chip status-${tone}`}>
      {label ?? normalized.replaceAll("_", " ")}
    </span>
  );
}
