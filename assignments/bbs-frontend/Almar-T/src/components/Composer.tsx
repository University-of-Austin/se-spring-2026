import { useId, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Link } from "react-router-dom";
import styles from "./Composer.module.css";

const MAX = 500;

export function Composer({
  currentUser,
  onSubmit,
}: {
  currentUser: string | null;
  /** resolves when the API call settles; throws to surface a server error inline */
  onSubmit: (message: string) => Promise<void>;
}) {
  const [value, setValue] = useState("");
  const [serverError, setServerError] = useState<string | null>(null);
  const [posting, setPosting] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const taId = useId();
  const errId = useId();

  const trimmed = value.trim();
  const tooLong = value.length > MAX;
  const empty = trimmed.length === 0;
  const canSubmit = !!currentUser && !empty && !tooLong && !posting;

  const submit = async () => {
    if (!canSubmit) return;
    setPosting(true);
    setServerError(null);
    try {
      await onSubmit(trimmed);
      setValue("");
      textareaRef.current?.focus();
    } catch (e) {
      const detail =
        e && typeof e === "object" && "detail" in e
          ? String((e as { detail: string }).detail)
          : String(e);
      setServerError(detail);
    } finally {
      setPosting(false);
    }
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      void submit();
    }
  };

  if (!currentUser) {
    return (
      <div className={styles.signedOut}>
        <p>
          <Link to="/sign-in">Sign in</Link> to post.
        </p>
      </div>
    );
  }

  const countClass = tooLong
    ? `${styles.count} ${styles.countOver}`
    : value.length > MAX - 50
      ? `${styles.count} ${styles.countWarn}`
      : styles.count;

  return (
    <form
      className={styles.composer}
      onSubmit={(e: FormEvent) => {
        e.preventDefault();
        void submit();
      }}
      aria-label="Compose a new post"
    >
      <div className={styles.head}>
        <label htmlFor={taId} className="label">
          Post as <span className={styles.author}>@{currentUser}</span>
        </label>
        <span className={countClass} aria-live="polite">
          {value.length}/{MAX}
        </span>
      </div>
      <textarea
        ref={textareaRef}
        id={taId}
        className="textarea"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="What's on your mind? (⌘+Enter to post)"
        rows={3}
        aria-invalid={tooLong || !!serverError}
        aria-describedby={serverError ? errId : undefined}
        disabled={posting}
      />
      {serverError && (
        <p id={errId} className="error-text" role="alert">
          {serverError}
        </p>
      )}
      <div className={styles.actions}>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={!canSubmit}
          aria-label="Post message"
        >
          {posting ? "Posting…" : "Post"}
        </button>
      </div>
    </form>
  );
}
