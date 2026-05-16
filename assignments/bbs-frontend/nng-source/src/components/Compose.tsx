import { useEffect, useRef, useState } from "react";
import { useAuth } from "../auth";
import type { Board, Post } from "../types";
import { api } from "../api";

const MAX_LEN = 500;
const BOARD_RE = /^[a-z0-9_-]+$/;
const BOARD_MAX = 30;

interface ComposeProps {
  onOptimisticAdd: (placeholder: Post) => void;
  onConfirm: (placeholderId: number, real: Post) => void;
  onRollback: (placeholderId: number) => void;
  /** If set, the board is locked (we're inside a board context). */
  board?: string;
}

let placeholderCounter = -1;

export function Compose({ onOptimisticAdd, onConfirm, onRollback, board }: ComposeProps) {
  const { username, token } = useAuth();
  const [text, setText] = useState("");
  const [boardInput, setBoardInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [boards, setBoards] = useState<Board[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Fetch board names for the autocomplete datalist. Cheap, runs once on mount.
  // If it fails we just don't show suggestions; the input is still free-text.
  useEffect(() => {
    let cancelled = false;
    api.listBoards()
      .then((bs) => { if (!cancelled) setBoards(bs); })
      .catch(() => { /* ignore */ });
    return () => { cancelled = true; };
  }, []);

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

  // Board: if locked by URL context, use that. Otherwise validate the input.
  const effectiveBoard = board || boardInput.trim().toLowerCase();
  const boardSpecified = effectiveBoard.length > 0;
  const boardInvalid =
    boardSpecified && (!BOARD_RE.test(effectiveBoard) || effectiveBoard.length > BOARD_MAX);

  const disabled = submitting || isEmpty || tooLong || boardInvalid;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (disabled) return;
    setSubmitting(true);
    setError(null);

    const targetBoard = effectiveBoard || "general";
    const placeholderId = placeholderCounter--;
    const optimistic: Post = {
      id: placeholderId,
      username: username!,
      board: targetBoard,
      message: trimmed,
      created_at: new Date().toISOString(),
      updated_at: null,
    };
    onOptimisticAdd(optimistic);
    setText("");

    try {
      const real = await api.createPost(
        trimmed,
        username!,
        token!,
        effectiveBoard || undefined,
      );
      onConfirm(placeholderId, real);
    } catch (err) {
      onRollback(placeholderId);
      setError(err instanceof Error ? err.message : "Could not post.");
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

      <div className="compose-board-row">
        {board ? (
          <span className="compose-board-locked">
            Posting to <strong>#{board}</strong>
          </span>
        ) : (
          <>
            <label htmlFor="compose-board" className="compose-board-label">
              Board
            </label>
            <input
              id="compose-board"
              type="text"
              className="compose-board-input"
              list="compose-board-options"
              placeholder="general"
              value={boardInput}
              onChange={(e) => setBoardInput(e.target.value)}
              maxLength={BOARD_MAX}
              autoComplete="off"
              aria-invalid={boardInvalid}
            />
            <datalist id="compose-board-options">
              {boards.map((b) => (
                <option key={b.name} value={b.name} />
              ))}
            </datalist>
          </>
        )}
      </div>
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
      {boardInvalid && (
        <div role="alert" className="inline-error">
          Board name must be lowercase letters, digits, <code>_</code>, or <code>-</code>.
        </div>
      )}
      {error && (
        <div id="compose-error" role="alert" className="inline-error">
          {error}
        </div>
      )}
    </form>
  );
}
