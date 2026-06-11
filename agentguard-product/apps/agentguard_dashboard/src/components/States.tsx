export function LoadingState({ label = "Loading" }: { label?: string }) {
  return <div className="loading-state">{label}…</div>;
}

export function ErrorState({ message }: { message: string }) {
  return <div className="error-state">{message}</div>;
}

export function EmptyState({
  title,
  message,
}: {
  title: string;
  message: string;
}) {
  return (
    <div className="empty-state">
      <div>
        <strong style={{ color: "white" }}>{title}</strong>
        <div style={{ marginTop: 8 }}>{message}</div>
      </div>
    </div>
  );
}
