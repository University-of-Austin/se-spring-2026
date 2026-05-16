import { useEffect, useRef, useState } from "react";
import { useAuth } from "../auth";
import type { Post } from "../types";
import { api } from "../api";

const MAX_LEN = 500;

interface ComposeProps {
  onOptimisticAdd: (placeholder: Post) => void;
  onConfirm: (placeholderId: number, real: Post) => void;
  onRollback: (placeholderId: number) => void;
  board?: string;
}

let placeholderCounter = -1;

export function Compose({ onOptimisticAdd, onConfirm, onRollback, board }: ComposeProps) {
  const { username, token } = useAuth();
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Cmd/Ctrl+Enter to submit
  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      const form = e.currentTarget.form;
      if (form) form.requestSubmit();
    }
  }

  // Listen for global "focus compose" shortcut event from app shell.
  useEffect(() => {
    function handler() {
      textareaRef.current?.focus();
    }
    window.addEventListener("bbs:focus-compose", handler);
    return () => window.removeEventListener("bbs:focus-compose", handler);
  }, []);

  if (!username || !token) {
    return (
      <div className="compose compose-locked">
        <p>You're not signed in. <a href="/login">Log in</a> to post.</p>
      </div>
    );
  }

  const trimmed = text.trim();
  const isEmpty = trimmed.length === 0;
  const tooLong = text.length > MAX_LEN;
  const disabled = submitting || isEmpty || tooLong;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (disabled) return;
    setSubmitting(true);
    setError(null);

    const placeholderId = placeholderCounter--;
    const optimistic: Post = {
      id: placeholderId,
      username: username!,
      board: board || "general",
      message: trimmed,
      created_at: new Date().toISOString(),
      updated_at: null,
    };
    onOptimisticAdd(optimistic);
    setText("");

    try {
      const real = await api.createPost(trimmed, username!, token!, board);
      onConfirm(placeholderId, real);
    } catch (err) {
      onRollback(placeholderId);
      setError(err instanceof Error ? err.message : "Could not post.");
      // restore the draft so the user doesn't lose what they typed
      setText(trimmed);
    } finally {
      setSubmitting(false);
    }
  }

  const countClass = tooLong ? "char-count char-count-over" : "char-count";

  return (
    <form onSubmit={handleSubmit} className="compose" aria-label="Compose a new post">
      <label htmlFor="compose-textarea" className="visually-hidden">Message</label>
      <textarea
        id="compose-textarea"
        ref={textareaRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="What's on your mind? (Cmd/Ctrl+Enter to post)"
        rows={3}
        aria-describedby="compose-count compose-error"
        aria-invalid={tooLong}
      />
      <div className="compose-footer">
        <span id="compose-count" className={countClass} aria-live="polite">
          {text.length} / {MAX_LEN}
        </span>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={disabled}
          aria-label="Post message"
        >
          {submitting ? "Posting..." : "Post"}
        </button>
      </div>
      {error && (
        <div id="compose-error" role="alert" className="inline-error">
          {error}
        </div>
      )}
    </form>
  );
}
