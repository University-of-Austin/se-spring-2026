import { useId, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api } from "../lib/api";
import type { Post } from "../lib/types";
import { useCurrentUser } from "../hooks/useCurrentUser";
import styles from "./ComposeForm.module.css";

const MAX = 500;

export function ComposeForm({
  onPosted,
}: {
  onPosted?: (post: Post) => void;
}) {
  const username = useCurrentUser();
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const fieldId = useId();
  const errorId = useId();

  if (!username) {
    return (
      <div className={styles.signedOut}>
        <Link to="/signup">Sign in</Link> to post.
      </div>
    );
  }

  const trimmed = text.trim();
  const over = text.length > MAX;
  // Disable if empty, server max exceeded, or already mid-flight. The server
  // is the ultimate authority; this just prevents the obvious 422.
  const disabled = trimmed.length === 0 || over || submitting;

  const submit = async () => {
    if (disabled) return;
    setSubmitting(true);
    setError(null);
    try {
      const post = await api.createPost(text, username);
      setText("");
      onPosted?.(post);
    } catch (e) {
      // Server validation wins — show its message verbatim instead of swallowing.
      setError(
        e instanceof ApiError ? e.message : (e as Error).message ?? "Post failed",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      void submit();
    }
  };

  return (
    <form
      className={styles.form}
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
      aria-labelledby={`${fieldId}-label`}
    >
      <label htmlFor={fieldId} id={`${fieldId}-label`} className={styles.label}>
        what's on your mind, @{username}?
      </label>
      <textarea
        id={fieldId}
        className={styles.textarea}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        maxLength={MAX * 2} // soft cap; server enforces the hard 500
        placeholder="say something…"
        aria-describedby={error ? errorId : undefined}
        aria-invalid={over || !!error}
      />
      {error && (
        <div id={errorId} role="alert" className={styles.error}>
          {error}
        </div>
      )}
      <div className={styles.footer}>
        <span className={styles.hint}>
          <kbd>⌘</kbd>+<kbd>Enter</kbd> to post
        </span>
        <div className={styles.footer}>
          <span
            className={`${styles.count} ${over ? styles.countOver : ""}`}
            aria-live="polite"
          >
            {text.length}/{MAX}
          </span>
          <button
            type="submit"
            className={styles.submit}
            disabled={disabled}
          >
            {submitting ? "posting…" : "post"}
          </button>
        </div>
      </div>
    </form>
  );
}
