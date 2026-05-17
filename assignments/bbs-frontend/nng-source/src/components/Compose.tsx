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

const IMAGE_MAX_BYTES = 5_000_000;
const IMAGE_MIME_RE = /^image\/(png|jpeg|webp|gif)$/;

export function Compose({ onOptimisticAdd, onConfirm, onRollback, board }: ComposeProps) {
  const { username, token } = useAuth();
  const [text, setText] = useState("");
  const [boardInput, setBoardInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [boards, setBoards] = useState<Board[]>([]);
  const [image, setImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

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

  // Revoke the object URL when the image changes / unmounts to avoid leaks.
  useEffect(() => {
    if (!image) { setImagePreview(null); return; }
    const url = URL.createObjectURL(image);
    setImagePreview(url);
    return () => URL.revokeObjectURL(url);
  }, [image]);

  function onPickImage(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = "";  // allow re-picking the same file
    if (!f) return;
    if (!IMAGE_MIME_RE.test(f.type)) {
      setError("Image must be PNG, JPG, WebP, or GIF.");
      return;
    }
    if (f.size > IMAGE_MAX_BYTES) {
      setError(`Image too large (max ${IMAGE_MAX_BYTES / 1_000_000} MB).`);
      return;
    }
    setError(null);
    setImage(f);
  }
  function clearImage() { setImage(null); }

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
    const attachedImage = image;
    const optimistic: Post = {
      id: placeholderId,
      username: username!,
      board: targetBoard,
      message: trimmed,
      created_at: new Date().toISOString(),
      updated_at: null,
      avatar_url: null,
      image_url: imagePreview,
    };
    onOptimisticAdd(optimistic);
    setText("");
    setImage(null);

    try {
      const real = await api.createPost(trimmed, username!, token!, {
        board: effectiveBoard || undefined,
        image: attachedImage,
      });
      onConfirm(placeholderId, real);
    } catch (err) {
      onRollback(placeholderId);
      setError(err instanceof Error ? err.message : "Could not post.");
      setText(trimmed);
      setImage(attachedImage);
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
      {imagePreview && (
        <div className="compose-image-preview" role="group" aria-label="Attached image preview">
          <img src={imagePreview} alt="" />
          <button
            type="button"
            className="btn btn-link btn-danger btn-sm compose-image-clear"
            onClick={clearImage}
            aria-label="Remove attached image"
          >
            Remove image
          </button>
        </div>
      )}

      <div className="compose-footer">
        <span id="compose-count" className={countClass} aria-live="polite">
          {text.length} / {MAX_LEN}
        </span>
        <div className="compose-footer-actions">
          <input
            ref={imageInputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp,image/gif"
            onChange={onPickImage}
            className="visually-hidden"
            aria-label="Attach image"
          />
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => imageInputRef.current?.click()}
            disabled={submitting}
            aria-label={image ? "Replace attached image" : "Attach image"}
            title="Attach image (PNG/JPG/WebP/GIF, up to 5 MB)"
          >
            {image ? "🖼 Change" : "🖼 Attach"}
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={disabled}
            aria-label="Post message"
          >
            {submitting ? "Posting..." : "Post"}
          </button>
        </div>
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
