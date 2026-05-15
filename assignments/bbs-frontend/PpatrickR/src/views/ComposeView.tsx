import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createPost } from "../api/posts";
import { ApiError } from "../api/types";

const MAX = 500;

export function ComposeView({ username }: { username: string }) {
  const navigate = useNavigate();
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [postedId, setPostedId] = useState<number | null>(null);

  const trimmed = message.trim();
  const len = message.length;
  const overLimit = len > MAX;
  const canSubmit = trimmed.length > 0 && !overLimit && !submitting;

  async function submit() {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    setPostedId(null);
    try {
      const post = await createPost(message, username);
      setMessage("");
      setPostedId(post.id);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setError(
          `The server has no user named @${username}. Sign in again to create or switch to a real account.`,
        );
      } else {
        setError(err instanceof ApiError ? err.detail : String(err));
      }
    } finally {
      setSubmitting(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      submit();
    }
  }

  return (
    <section className="view compose-view">
      <h1>Compose</h1>
      <p className="muted">
        Posting as <strong>@{username}</strong>. Cmd/Ctrl+Enter to post.
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <label htmlFor="compose-textarea" className="sr-only">
          New post message
        </label>
        <textarea
          id="compose-textarea"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={onKeyDown}
          rows={5}
          placeholder="What's on your mind?"
          aria-invalid={overLimit}
          autoFocus
        />
        <div className="compose-foot">
          <span
            className={"char-count" + (overLimit ? " err" : "")}
            aria-live="polite"
          >
            {len} / {MAX}
          </span>
          <button type="submit" className="primary" disabled={!canSubmit}>
            {submitting ? "Posting…" : "Post"}
          </button>
        </div>

        {error && (
          <div className="status error" role="alert">
            <div className="error-detail">{error}</div>
          </div>
        )}

        {postedId !== null && (
          <div className="status ok" role="status">
            Posted.{" "}
            <Link to={`/posts/${postedId}`} className="link-btn">
              View it
            </Link>{" "}
            or{" "}
            <button
              type="button"
              className="link-btn"
              onClick={() => navigate("/")}
            >
              go to feed
            </button>
            .
          </div>
        )}
      </form>
    </section>
  );
}
