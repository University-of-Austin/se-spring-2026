export function Skeleton({ count = 3 }: { count?: number }) {
  return (
    <div aria-label="Loading" aria-busy="true">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton" />
      ))}
    </div>
  );
}
