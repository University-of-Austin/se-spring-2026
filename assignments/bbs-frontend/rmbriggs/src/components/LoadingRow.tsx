export default function LoadingRow({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="py-6 text-center text-sm text-neutral-500" role="status" aria-live="polite">
      {label}
    </div>
  );
}
