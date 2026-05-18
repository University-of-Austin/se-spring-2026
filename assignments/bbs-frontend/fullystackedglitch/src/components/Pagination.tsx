import styles from "./Pagination.module.css";

// The API doesn't return a total count, so we can't render the full range up
// front. Instead we show: Prev | known pages (1..max seen) | maybe-next | Next.
// `hasNext` is computed by the caller from `posts.length === pageSize`.
export function Pagination({
  page,
  hasNext,
  onChange,
}: {
  page: number;
  hasNext: boolean;
  onChange: (page: number) => void;
}) {
  const known = Math.max(page, 1);
  const visible: number[] = [];
  for (let i = 1; i <= known; i++) visible.push(i);
  if (hasNext) visible.push(known + 1);

  // If we're far from page 1, collapse the middle to keep the bar short on
  // mobile.
  const compact = visible.length > 5;
  const display: (number | "gap")[] = [];
  if (compact) {
    display.push(1);
    if (page > 3) display.push("gap");
    for (let i = Math.max(2, page - 1); i <= Math.min(known, page + 1); i++) {
      display.push(i);
    }
    if (hasNext) display.push(known + 1);
  } else {
    display.push(...visible);
  }

  return (
    <nav className={styles.bar} aria-label="Pagination">
      <button
        type="button"
        className={styles.btn}
        onClick={() => onChange(page - 1)}
        disabled={page <= 1}
        aria-label="Previous page"
      >
        ← prev
      </button>
      {display.map((d, i) =>
        d === "gap" ? (
          <span key={`gap-${i}`} className={styles.gap} aria-hidden="true">
            …
          </span>
        ) : (
          <button
            key={d}
            type="button"
            className={`${styles.btn} ${d === page ? styles.btnActive : ""}`}
            onClick={() => onChange(d)}
            aria-current={d === page ? "page" : undefined}
            aria-label={`Page ${d}`}
          >
            {d}
          </button>
        ),
      )}
      <button
        type="button"
        className={styles.btn}
        onClick={() => onChange(page + 1)}
        disabled={!hasNext}
        aria-label="Next page"
      >
        next →
      </button>
    </nav>
  );
}
