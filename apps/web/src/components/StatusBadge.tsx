const styles: Record<string, string> = {
  allow: "bg-[var(--green-bg)] text-[var(--green)]",
  executed: "bg-[var(--green-bg)] text-[var(--green)]",
  operational: "bg-[var(--green-bg)] text-[var(--green)]",
  warn: "bg-[var(--amber-bg)] text-[var(--amber)]",
  review: "bg-[var(--amber-bg)] text-[var(--amber)]",
  require_approval: "bg-[var(--amber-bg)] text-[var(--amber)]",
  paused: "bg-[var(--amber-bg)] text-[var(--amber)]",
  degraded: "bg-[var(--amber-bg)] text-[var(--amber)]",
  block: "bg-[var(--red-bg)] text-[var(--red)]",
  blocked: "bg-[var(--red-bg)] text-[var(--red)]",
  unavailable: "bg-[var(--red-bg)] text-[var(--red)]",
  running: "bg-blue-100 text-blue-700",
  completed: "bg-slate-100 text-slate-700",
  idle: "bg-slate-100 text-slate-600",
};

export function StatusBadge({ value }: { value: string }) {
  return (
    <span
      className={`inline-flex rounded px-2 py-1 text-[10px] font-bold uppercase tracking-[0.05em] ${styles[value] ?? "bg-slate-100 text-slate-700"}`}
    >
      {value.replaceAll("_", " ")}
    </span>
  );
}
