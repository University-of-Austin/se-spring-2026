import { useEffect, useState } from "react";
import { useKeyboardShortcuts } from "../hooks/useKeyboardShortcuts";
import styles from "./ShortcutOverlay.module.css";

const SHORTCUTS: { label: string; keys: string[] }[] = [
  { label: "Show this help", keys: ["?"] },
  { label: "Focus search on feed", keys: ["/"] },
  { label: "Submit a post", keys: ["⌘", "Enter"] },
  { label: "Close this overlay", keys: ["Esc"] },
];

export function ShortcutOverlay() {
  const [open, setOpen] = useState(false);

  useKeyboardShortcuts([
    { key: "?", handler: () => setOpen((o) => !o) },
    { key: "Escape", allowInInput: true, handler: () => setOpen(false) },
  ]);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  if (!open) return null;

  return (
    <div
      className={styles.backdrop}
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
      onClick={() => setOpen(false)}
    >
      <div className={styles.panel} onClick={(e) => e.stopPropagation()}>
        <h2 className={styles.title}>Keyboard shortcuts</h2>
        <ul className={styles.list}>
          {SHORTCUTS.map((s) => (
            <li key={s.label} className={styles.row}>
              <span className={styles.label}>{s.label}</span>
              <span className={styles.keys}>
                {s.keys.map((k) => (
                  <kbd key={k}>{k}</kbd>
                ))}
              </span>
            </li>
          ))}
        </ul>
        <button
          type="button"
          className={styles.close}
          onClick={() => setOpen(false)}
        >
          Close
        </button>
      </div>
    </div>
  );
}
