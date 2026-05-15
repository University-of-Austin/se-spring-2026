// Top-of-screen 2px bar that shows during background refetches (polling tick,
// query-key change). Distinct from the full skeleton, which only shows when
// there's no data yet.
export function RevalidatingBar({ active }: { active: boolean }) {
  if (!active) return null;
  return <div className="revalidating-bar" aria-hidden="true" />;
}
