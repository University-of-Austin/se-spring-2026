// Compose a new post.
//
// At silver tier, submit is optimistic: we hand the message off to
// OptimisticPostsContext which makes it appear in the feed
// immediately, then we navigate to the feed.  The actual POST is
// owned by the context, so it survives this view unmounting.
//
// Validation lives in two places:
//   - Client: disable Submit on empty / over-length input.
//   - Server: still authoritative.  Failed posts surface in the feed
//     as a "failed" pending entry with the server's detail string —
//     this view never sees the error directly because we navigate
//     away before it returns.

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCurrentUser } from "../hooks/useCurrentUser";
import { useOptimisticPosts } from "../hooks/useOptimisticPosts";
import { paths } from "../router/paths";
import styles from "./ComposeView.module.css";

const MAX_LENGTH = 500;

export function ComposeView() {
  const { username } = useCurrentUser();
  const { submit } = useOptimisticPosts();
  const navigate = useNavigate();

  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const trimmed = message.trim();
  const tooLong = message.length > MAX_LENGTH;
  const canSubmit = !!username && trimmed.length > 0 && !tooLong && !submitting;

  async function onSubmit() {
    if (!canSubmit) return;
    setSubmitting(true);
    const messageToSend = message;
    setMessage(""); // optimistic input clear
    // Fire and forget — the optimistic context owns the lifecycle.
    submit(messageToSend, username!);
    navigate(paths.feed());
    setSubmitting(false);
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
            onClick={() => navigate(paths.identity())}
          >
            Set a username
          </button>
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
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
              onSubmit();
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
          <button type="submit" className={styles.submit} disabled={!canSubmit}>
            Post
          </button>
        </div>
      </form>
    </div>
  );
}
