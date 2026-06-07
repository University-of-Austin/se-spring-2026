// Inline compose form. Used both at the top of the Feed (Substack-style)
// and inside the standalone /compose route.

import { useState, type FormEvent, type KeyboardEvent } from "react";
import { Link } from "react-router-dom";
import { useCreatePost } from "../hooks/usePosts";
import { useUsername } from "../hooks/useUsername";
import { errorText } from "../lib/errorText";
import { ErrorMessage } from "./ErrorMessage";
import styles from "./ComposeForm.module.css";

const MAX_LEN = 500;

interface Props {
  // When true, render a more compact version suitable for inline use at
  // the top of the feed. Defaults to false (full-card layout).
  inline?: boolean;
  onPosted?: () => void;
}

export function ComposeForm({ inline = false, onPosted }: Props) {
  const { username } = useUsername();
  const createPost = useCreatePost(username);

  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);

  const trimmedLen = message.trim().length;
  const overLimit = message.length > MAX_LEN;
  const canSubmit = !!username && trimmedLen >= 1 && !overLimit && !createPost.isPending;

  async function handleSubmit(e?: FormEvent) {
    e?.preventDefault();
    if (!canSubmit) return;
    setError(null);
    try {
      await createPost.mutateAsync(message);
      setMessage("");
      onPosted?.();
    } catch (err) {
      setError(errorText(err, "Failed to post. Try again."));
    }
  }

  // Cmd+Enter / Ctrl+Enter to post.
  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      void handleSubmit();
    }
  }

  if (!username) {
    return (
      <div className={`${styles.card} ${inline ? styles.inline : ""}`}>
        <p className={styles.signinHint}>
          <Link to="/signin">Choose a username</Link> to start posting.
        </p>
      </div>
    );
  }

  const countClass = overLimit
    ? `${styles.count} ${styles.countOver}`
    : message.length > MAX_LEN - 50
      ? `${styles.count} ${styles.countWarn}`
      : styles.count;

  return (
    <form
      onSubmit={handleSubmit}
      className={`${styles.card} ${inline ? styles.inline : ""}`}
      aria-label="Compose a new post"
    >
      <label htmlFor={inline ? "inline-compose" : "page-compose"} className={styles.srOnly}>
        Message
      </label>
      <textarea
        id={inline ? "inline-compose" : "page-compose"}
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={`What do you want to share, ${username}?`}
        rows={inline ? 2 : 5}
        aria-describedby={inline ? "inline-count" : "page-count"}
        className={styles.textarea}
      />
      <div className={styles.row}>
        <span id={inline ? "inline-count" : "page-count"} className={countClass} aria-live="polite">
          {message.length} / {MAX_LEN}
        </span>
        <div className={styles.actions}>
          <button type="submit" disabled={!canSubmit} className={styles.primary}>
            {createPost.isPending ? "Posting..." : "Post"}
          </button>
        </div>
      </div>
      {error && <ErrorMessage message={error} />}
    </form>
  );
}
