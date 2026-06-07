// Sticky banner that appears at the top of the feed when polling has detected
// posts the user hasn't seen yet. Clicking the banner refetches the feed and
// scrolls to the top so the new posts come into view.

import styles from "./NewPostsBanner.module.css";

interface Props {
  count: number;
  onClick: () => void;
}

export function NewPostsBanner({ count, onClick }: Props) {
  if (count <= 0) return null;
  return (
    <button type="button" onClick={onClick} className={styles.banner}>
      ↑ {count} new {count === 1 ? "post" : "posts"}
    </button>
  );
}
