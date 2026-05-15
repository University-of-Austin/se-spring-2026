import { useRouter } from "../router/useRouter";
import styles from "./NotFoundView.module.css";

export function NotFoundView({ what }: { what: string }) {
  const { navigate } = useRouter();
  return (
    <div className={styles.wrap}>
      <h2 className={styles.title}>Not found</h2>
      <p className={styles.body}>{what} doesn't exist (or no longer exists).</p>
      <button type="button" className={styles.button} onClick={() => navigate({ view: "feed" })}>
        Back to feed
      </button>
    </div>
  );
}
