import { LoadingDots } from "./LoadingDots";
import styles from "./Pagination.module.css";

export function LoadMore({
  hasMore,
  loading,
  onLoad,
}: {
  hasMore: boolean;
  loading: boolean;
  onLoad: () => void;
}) {
  if (loading) {
    return (
      <div className={styles.wrap}>
        <LoadingDots label="Loading more" />
      </div>
    );
  }
  if (!hasMore) {
    return <p className={styles.end}>You've reached the end.</p>;
  }
  return (
    <div className={styles.wrap}>
      <button type="button" className="btn" onClick={onLoad}>
        Load more
      </button>
    </div>
  );
}
