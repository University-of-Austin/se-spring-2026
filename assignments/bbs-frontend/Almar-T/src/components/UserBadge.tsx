import { Link } from "react-router-dom";
import styles from "./UserBadge.module.css";

export function UserBadge({
  username,
  prefix = "@",
}: {
  username: string;
  prefix?: string;
}) {
  return (
    <Link to={`/users/${encodeURIComponent(username)}`} className={styles.badge}>
      {prefix}
      {username}
    </Link>
  );
}
