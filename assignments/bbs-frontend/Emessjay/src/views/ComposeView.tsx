// Compose a new post.
//
// Validation lives in two places, deliberately:
//   - Client (this file): disable Submit on empty/over-length input
//     so the obvious mistakes don't even reach the server.
//   - Server: still authoritative.  We render any 422 detail inline,
//     never suppress one because client-side thought the input was
//     fine.  ("Do not eat it" — assignment, verbatim.)
//
// Keyboard: Cmd+Enter / Ctrl+Enter submits from the textarea, which
// matches Slack/Discord muscle memory.

import { useState } from "react";
import { useCurrentUser } from "../hooks/useCurrentUser";
import { useRouter } from "../router/useRouter";
import { createPost } from "../api/endpoints";
import { ApiError } from "../api/client";
import { ApiErrorMessage } from "../components/ApiErrorMessage";
import styles from "./ComposeView.module.css";

const MAX_LENGTH = 500;

export function ComposeView() {
  const { username } = useCurrentUser();
  const { navigate } = useRouter();

  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const trimmed = message.trim();
  const tooLong = message.length > MAX_LENGTH;
  const canSubmit = !!username && trimmed.length > 0 && !tooLong && !submitting;

  async function submit() {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      await createPost(message, username!);
      setMessage("");
      navigate({ view: "feed" });
    } catch (err) {
      if (err instanceof ApiError) setError(err);
      else setError(new ApiError(0, "Unexpected error"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.wrap}>
      <h2 className={styles.title}>New post</h2>

      {!username && (
        <div className={styles.signinPrompt}>
          <p>You need a username before you can post.</p>
          <button
            type="button"
            className={styles.signinButton}
            onClick={() => navigate({ view: "identity" })}
          >
            Set a username
          </button>
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className={styles.form}
      >
        <label htmlFor="compose-message" className={styles.label}>
          Message
        </label>
        <textarea
          id="compose-message"
          className={styles.textarea}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
              e.preventDefault();
              submit();
            }
          }}
          rows={5}
          placeholder="Say something…"
          disabled={!username || submitting}
        />

        <div className={styles.controls}>
          <span className={`${styles.counter} ${tooLong ? styles.counterBad : ""}`}>
            {message.length} / {MAX_LENGTH}
          </span>
          <span className={styles.hint}>⌘⏎ / Ctrl+⏎ to post</span>
          <button
            type="submit"
            className={styles.submit}
            disabled={!canSubmit}
          >
            {submitting ? "Posting…" : "Post"}
          </button>
        </div>

        {error && <ApiErrorMessage error={error} />}
      </form>
    </div>
  );
}
