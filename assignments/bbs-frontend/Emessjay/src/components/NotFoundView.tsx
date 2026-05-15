import { useNavigate } from "react-router-dom";
import { paths } from "../router/paths";
import styles from "./NotFoundView.module.css";

export function NotFoundView({ what }: { what: string }) {
  const navigate = useNavigate();
  return (
    <div className={styles.wrap}>
      <h2 className={styles.title}>Not found</h2>
      <p className={styles.body}>{what} doesn't exist (or no longer exists).</p>
      <button type="button" className={styles.button} onClick={() => navigate(paths.feed())}>
        Back to feed
      </button>
    </div>
  );
}
