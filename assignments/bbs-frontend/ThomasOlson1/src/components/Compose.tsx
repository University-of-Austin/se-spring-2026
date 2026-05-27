import { useEffect, useRef, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import type { Post } from "../api/client";
import { createPost } from "../api/posts";
import { ApiError } from "../api/client";

const MAX = 500;

type Props = {
  onCreated?: (p: Post) => void;
  onOptimistic?: (tempPost: Post) => void;
  onRollback?: (tempId: number, errMsg: string) => void;
  onReconcile?: (tempId: number, real: Post) => void;
};

let tempCounter = -1;

export function Compose({ onCreated, onOptimistic, onRollback, onReconcile }: Props) {
  const { username } = useAuth();
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const taRef = useRef<HTMLTextAreaElement | null>(null);

  const trimmed = text.trim();
  const tooLong = text.length > MAX;
  const canSubmit = !!username && trimmed.length > 0 && !tooLong && !submitting;

  async function submit() {
    if (!canSubmit || !username) return;
    setError(null);
    const tempId = tempCounter--;
    const optimistic: Post = {
      id: tempId,
      username,
      message: trimmed,
      created_at: new Date().toISOString().replace(/\.\d+Z$/, ""),
      updated_at: null,
      board: "general",
    };
    onOptimistic?.(optimistic);
    setSubmitting(true);
    const draft = text;
    setText("");
    try {
      const real = await createPost(trimmed, username);
      onReconcile?.(tempId, real);
      onCreated?.(real);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Failed to post";
      onRollback?.(tempId, msg);
      setText(draft);
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        if (document.activeElement === taRef.current) {
          e.preventDefault();
          submit();
        }
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, username, submitting]);

  if (!username) {
    return (
      <div className="compose compose-locked">
        <p>
          You need to <a href="/signup">sign in or create a user</a> to post.
        </p>
      </div>
    );
  }

  const countClass = tooLong ? "compose-count over" : text.length > MAX * 0.8 ? "compose-count warn" : "compose-count";

  return (
    <form
      className="compose"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <label htmlFor="compose-msg" className="visually-hidden">
        New post
      </label>
      <textarea
        id="compose-msg"
        ref={taRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={`What's on your mind, @${username}?`}
        rows={3}
        aria-invalid={tooLong || !!error}
        aria-describedby="compose-count compose-error"
      />
      <div className="compose-row">
        <span id="compose-count" className={countClass}>
          {text.length}/{MAX}
        </span>
        <button type="submit" className="btn btn-primary" disabled={!canSubmit}>
          {submitting ? "Posting…" : "Post (⌘↵)"}
        </button>
      </div>
      {error && (
        <p id="compose-error" className="compose-error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
