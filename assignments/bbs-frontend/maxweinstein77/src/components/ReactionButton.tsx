// Heart-reaction button for a single post. Click toggles between
// "I have reacted" and "I haven't" with optimistic updates.

import { useReactions, useToggleReaction } from "../hooks/useReactions";
import { useUsername } from "../hooks/useUsername";
import styles from "./ReactionButton.module.css";

interface Props {
  postId: number;
}

export function ReactionButton({ postId }: Props) {
  const { username } = useUsername();
  const reactions = useReactions(postId);
  const toggle = useToggleReaction(postId, username);

  const list = reactions.data ?? [];
  const count = list.length;
  const reacted = !!username && list.some((r) => r.username === username);

  function handleClick() {
    if (!username) return;
    toggle.mutate(reacted);
  }

  const ariaLabel = reacted ? `Unlike (currently ${count})` : `Like (currently ${count})`;

  // Tooltip lists who reacted. Falls back to a hint when no one has yet
  // or the user isn't signed in.
  const tooltip = !username
    ? "Choose a username to react"
    : count === 0
      ? reacted ? "You liked this" : "Be the first to like this"
      : formatReactorList(list.map((r) => r.username), username);

  return (
    <span className={styles.wrap}>
      <button
        type="button"
        onClick={handleClick}
        disabled={!username || toggle.isPending}
        className={`${styles.btn} ${reacted ? styles.active : ""}`}
        aria-label={ariaLabel}
      >
        <span className={styles.heart} aria-hidden="true">{reacted ? "♥" : "♡"}</span>
        <span className={styles.count}>{count}</span>
      </button>
      <span className={styles.tooltip} role="tooltip">{tooltip}</span>
    </span>
  );
}

// Build a readable "X, Y, and Z liked this" string, replacing the current
// user with "You" so the tooltip reflects what the user sees.
function formatReactorList(usernames: string[], me: string): string {
  const display = usernames.map((u) => (u === me ? "You" : u));
  // Put "You" first if present.
  display.sort((a, b) => (a === "You" ? -1 : b === "You" ? 1 : 0));
  let joined: string;
  if (display.length === 1) joined = display[0];
  else if (display.length === 2) joined = `${display[0]} and ${display[1]}`;
  else joined = `${display.slice(0, -1).join(", ")}, and ${display[display.length - 1]}`;
  return `${joined} liked this`;
}
