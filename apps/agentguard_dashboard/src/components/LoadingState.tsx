export function LoadingState({ label = "Loading data" }: { label?: string }) {
  return (
    <div className="panel flex min-h-40 items-center justify-center text-sm text-[var(--ink-muted)]">
      {label}...
    </div>
  );
}
