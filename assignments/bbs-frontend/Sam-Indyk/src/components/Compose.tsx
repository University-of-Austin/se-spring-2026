import { type FormEvent, type KeyboardEvent, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api } from "../api/client";
import { MESSAGE_MAX, MESSAGE_MIN } from "../api/types";
import type { Post } from "../api/types";
import { useUser } from "../hooks/useUser";

export interface ComposeProps {
  /**
   * Called optimistically with a pending Post as soon as the user submits.
   * The Post has a synthetic negative id; the parent should swap it out
   * with the server-returned Post once `onSettled` fires.
   */
  onOptimistic: (pending: Post) => void;
  /**
   * Called when the server responds — either with the real post (success)
   * or with an Error (failure). The parent reconciles its list.
   */
  onSettled: (result: { ok: true; post: Post; pendingId: number } | { ok: false; error: ApiError; pendingId: number }) => void;
}

let pendingCounter = -1;
function nextPendingId(): number {
  return pendingCounter--;
}

export function Compose({ onOptimistic, onSettled }: ComposeProps) {
  const { username } = useUser();
  const [value, setValue] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const trimmedLen = value.trim().length;
  const over = value.length > MESSAGE_MAX;
  const canSubmit =
    !!username && !submitting && trimmedLen >= MESSAGE_MIN && !over;

  async function submit() {
    if (!canSubmit) return;
    if (!username) return;
    setServerError(null);
    setSubmitting(true);

    const pendingId = nextPendingId();
    const pending: Post = {
      id: pendingId,
      username,
      message: value,
      created_at: new Date().toISOString(),
      updated_at: null,
      reactions: {},
    };

    // Optimistically tell the parent to prepend.
    onOptimistic(pending);
    const text = value;
    setValue("");

    try {
      const post = await api.createPost(text, username);
      onSettled({ ok: true, post, pendingId });
    } catch (err) {
      const apiErr =
        err instanceof ApiError
          ? err
          : new ApiError(0, String(err), err);
      setServerError(apiErr.message);
      // Restore the text so the user doesn't lose what they wrote.
      setValue(text);
      onSettled({ ok: false, error: apiErr, pendingId });
    } finally {
      setSubmitting(false);
      textareaRef.current?.focus();
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      submit();
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    submit();
  }

  if (!username) {
    return (
      <div className="post">
        <p style={{ color: "var(--text-dim)" }}>
          You need to be signed in to post.{" "}
          <Link to="/auth">Choose a username</Link>.
        </p>
      </div>
    );
  }

  return (
    <form className="post" onSubmit={handleSubmit} aria-label="Compose a message">
      <div className="field">
        <label className="field-label" htmlFor="compose-textarea">
          New post as {username}
        </label>
        <textarea
          id="compose-textarea"
          ref={textareaRef}
          className="textarea"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="What's on your mind?"
          maxLength={MESSAGE_MAX * 2 /* allow overflow so we can show the error */}
          aria-describedby="compose-hint compose-count"
          aria-invalid={over || !!serverError}
          disabled={submitting}
        />
        <div className="field-foot">
          <span id="compose-hint" className="field-hint">
            <kbd>Ctrl</kbd>/<kbd>⌘</kbd>+<kbd>Enter</kbd> to post
          </span>
          <span
            id="compose-count"
            className={`field-hint char-count${over ? " over" : ""}`}
          >
            {value.length}/{MESSAGE_MAX}
          </span>
        </div>
      </div>

      {serverError && (
        <div className="field-error" role="alert">
          {serverError}
        </div>
      )}

      <div className="btn-row" style={{ justifyContent: "flex-end" }}>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={!canSubmit}
          aria-disabled={!canSubmit}
        >
          {submitting ? (
            <>
              <span className="spinner" aria-hidden="true" /> Posting…
            </>
          ) : (
            "Post"
          )}
        </button>
      </div>
    </form>
  );
}
