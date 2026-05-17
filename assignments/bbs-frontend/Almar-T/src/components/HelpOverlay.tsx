import { useEffect, useRef } from "react";
import styles from "./HelpOverlay.module.css";

type Shortcut = { keys: string[]; label: string };

const SHORTCUTS: Shortcut[] = [
  { keys: ["?"], label: "Show this help" },
  { keys: ["g", "f"], label: "Go to feed" },
  { keys: ["g", "u"], label: "Go to users" },
  { keys: ["⌘", "Enter"], label: "Post (while composing)" },
  { keys: ["Esc"], label: "Close dialogs" },
];

export function HelpOverlay({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) closeRef.current?.focus();
  }, [open]);

  if (!open) return null;

  return (
    <div
      className={styles.backdrop}
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
    >
      <div className={styles.panel} onClick={(e) => e.stopPropagation()}>
        <div className={styles.head}>
          <h2>Keyboard shortcuts</h2>
          <button
            ref={closeRef}
            type="button"
            className="btn btn-ghost"
            onClick={onClose}
          >
            Close
          </button>
        </div>
        <ul className={styles.list}>
          {SHORTCUTS.map((s) => (
            <li key={s.label} className={styles.row}>
              <span>{s.label}</span>
              <span className={styles.keys}>
                {s.keys.map((k, i) => (
                  <kbd key={i} className={styles.kbd}>
                    {k}
                  </kbd>
                ))}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
