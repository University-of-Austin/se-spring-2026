// Modal overlay listing every keyboard shortcut in the app.
// Open/close state is owned by the parent (Layout) so both the floating
// "?" button and the "?" keyboard shortcut can toggle it.

import styles from "./ShortcutsOverlay.module.css";

interface Shortcut {
  keys: string[];
  description: string;
}

const SHORTCUTS: Shortcut[] = [
  { keys: ["?"], description: "Show this shortcuts panel" },
  { keys: ["Esc"], description: "Close this panel" },
  { keys: ["Ctrl / ⌘", "Enter"], description: "Post message (in Compose)" },
];

interface Props {
  open: boolean;
  onClose: () => void;
}

export function ShortcutsOverlay({ open, onClose }: Props) {
  if (!open) return null;

  return (
    <div
      className={styles.backdrop}
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="shortcuts-heading"
    >
      <div className={styles.panel} onClick={(e) => e.stopPropagation()}>
        <header className={styles.header}>
          <h2 id="shortcuts-heading" className={styles.heading}>Keyboard shortcuts</h2>
          <button
            type="button"
            onClick={onClose}
            className={styles.closeBtn}
            aria-label="Close shortcuts panel"
          >
            ×
          </button>
        </header>
        <ul className={styles.list}>
          {SHORTCUTS.map((s) => (
            <li key={s.description} className={styles.row}>
              <span className={styles.keys}>
                {s.keys.map((k, i) => (
                  <span key={i}>
                    {i > 0 && <span className={styles.plus}>+</span>}
                    <kbd className={styles.kbd}>{k}</kbd>
                  </span>
                ))}
              </span>
              <span className={styles.desc}>{s.description}</span>
            </li>
          ))}
        </ul>
        <footer className={styles.footer}>
          Press <kbd className={styles.kbd}>?</kbd> any time to reopen.
        </footer>
      </div>
    </div>
  );
}
