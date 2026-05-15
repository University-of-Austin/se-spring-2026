// A clickable username that navigates to the user's profile.
// Rendered as a real <button> for keyboard accessibility — never a
// <div onClick>.

import { useRouter } from "../router/useRouter";
import styles from "./UserLink.module.css";

export function UserLink({ username }: { username: string }) {
  const { navigate } = useRouter();
  return (
    <button
      type="button"
      className={styles.link}
      onClick={(e) => {
        e.stopPropagation();
        navigate({ view: "user", username });
      }}
    >
      @{username}
    </button>
  );
}
