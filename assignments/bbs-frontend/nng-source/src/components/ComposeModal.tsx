import { useEffect, useRef } from "react";
import { Compose } from "./Compose";
import type { Post } from "../types";

interface ComposeModalProps {
  onClose: () => void;
  /** If the user opened the modal from a /?board= view, lock the board. */
  board?: string;
}

/**
 * Modal wrapper around `<Compose>` that lives at the document root via a FAB
 * in Layout. Optimistic state still belongs to whichever Feed instance is
 * open; we relay the events through window so the Feed can react without
 * being coupled to this component.
 *
 * Events:
 *  - bbs:post-optimistic  detail: { post }          fires on submit click
 *  - bbs:post-confirmed   detail: { placeholderId, post }
 *  - bbs:post-rollback    detail: { placeholderId }
 */
export function ComposeModal({ onClose, board }: ComposeModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  // ESC closes the modal.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // Focus the message textarea when the modal mounts.
  useEffect(() => {
    const ta = dialogRef.current?.querySelector("textarea") as HTMLTextAreaElement | null;
    ta?.focus();
  }, []);

  // Lock body scroll while the modal is open.
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prev; };
  }, []);

  function onOptimisticAdd(post: Post) {
    window.dispatchEvent(new CustomEvent("bbs:post-optimistic", { detail: { post } }));
  }
  function onConfirm(placeholderId: number, real: Post) {
    window.dispatchEvent(
      new CustomEvent("bbs:post-confirmed", { detail: { placeholderId, post: real } }),
    );
    // Successful post → close the modal. Feed will swap the placeholder.
    onClose();
  }
  function onRollback(placeholderId: number) {
    window.dispatchEvent(
      new CustomEvent("bbs:post-rollback", { detail: { placeholderId } }),
    );
    // Failure: keep the modal open so the user sees the error and can retry.
  }

  return (
    <div
      className="modal-backdrop"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div
        ref={dialogRef}
        className="modal compose-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="compose-modal-title"
      >
        <header className="modal-header">
          <h2 id="compose-modal-title">New post</h2>
          <button
            type="button"
            className="modal-close"
            onClick={onClose}
            aria-label="Close compose dialog"
          >
            ×
          </button>
        </header>
        <Compose
          board={board}
          onOptimisticAdd={onOptimisticAdd}
          onConfirm={onConfirm}
          onRollback={onRollback}
        />
      </div>
    </div>
  );
}
