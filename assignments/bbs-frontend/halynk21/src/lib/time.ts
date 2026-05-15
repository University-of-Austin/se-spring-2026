// Relative time formatting. Pure-string in/out keeps it trivially testable
// and avoids importing a date lib.

export function relative(iso: string, now: number = Date.now()): string {
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return iso;

  const diff = Math.max(0, Math.floor((now - t) / 1000));
  if (diff < 5) return 'just now';
  if (diff < 60) return `${diff}s ago`;
  const m = Math.floor(diff / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d}d ago`;

  return new Date(t).toLocaleDateString();
}
