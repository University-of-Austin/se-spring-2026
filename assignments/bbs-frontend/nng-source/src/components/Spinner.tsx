export function Spinner({ label = "Loading..." }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="spinner">
      <span className="spinner-dot" aria-hidden="true" />
      <span className="spinner-label">{label}</span>
    </div>
  );
}
