export function ErrorState({ message }: { message: string }) {
  return (
    <div className="panel border-red-200 bg-red-50 p-5 text-sm text-red-800">
      {message}
    </div>
  );
}
