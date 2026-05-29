// Clickable username — a real <Link>, not a button.  React-router's
// Link emits a real <a href> so middle-click-to-open-in-new-tab and
// right-click-copy-link work as the user expects.

import { Link } from "react-router-dom";
import { paths } from "../router/paths";
import styles from "./UserLink.module.css";

export function UserLink({ username }: { username: string }) {
  return (
    <Link
      to={paths.user(username)}
      className={styles.link}
      onClick={(e) => e.stopPropagation()}
    >
      @{username}
    </Link>
  );
}
