export default function LoadingRow({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="py-6 text-center text-sm text-muted-foreground" role="status" aria-live="polite">
      {label}
    </div>
  );
}
