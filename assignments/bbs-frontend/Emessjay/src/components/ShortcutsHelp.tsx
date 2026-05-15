// Help overlay for keyboard shortcuts.  Toggled by "?" globally,
// closed by Escape or by clicking the backdrop.

import { useEffect } from "react";
import { useShortcuts } from "../hooks/useShortcuts";
import styles from "./ShortcutsHelp.module.css";

const ROWS: { keys: string[]; description: string }[] = [
  { keys: ["g", "f"], description: "Go to feed" },
  { keys: ["g", "c"], description: "Go to compose" },
  { keys: ["g", "u"], description: "Go to users" },
  { keys: ["g", "i"], description: "Go to identity" },
  { keys: ["n"], description: "New post" },
  { keys: ["/"], description: "Focus the search on the feed" },
  { keys: ["⌘", "⏎"], description: "Submit the post (in compose)" },
  { keys: ["?"], description: "Show / hide this help" },
  { keys: ["Esc"], description: "Close this help" },
];

export function ShortcutsHelp() {
  const { helpOpen, closeHelp } = useShortcuts();

  // Trap focus on the close button when opening, so Tab cycles
  // sensibly inside the modal.
  useEffect(() => {
    if (!helpOpen) return;
    const close = document.getElementById("shortcuts-close");
    close?.focus();
  }, [helpOpen]);

  if (!helpOpen) return null;

  return (
    <div className={styles.backdrop} onClick={closeHelp} role="presentation">
      <div
        className={styles.dialog}
        role="dialog"
        aria-modal="true"
        aria-labelledby="shortcuts-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header className={styles.header}>
          <h2 id="shortcuts-title" className={styles.title}>Keyboard shortcuts</h2>
          <button
            id="shortcuts-close"
            type="button"
            className={styles.close}
            onClick={closeHelp}
            aria-label="Close"
          >
            ×
          </button>
        </header>
        <table className={styles.table}>
          <tbody>
            {ROWS.map((row) => (
              <tr key={row.description}>
                <td className={styles.keysCell}>
                  {row.keys.map((k, i) => (
                    <span key={i}>
                      <kbd className={styles.kbd}>{k}</kbd>
                      {i < row.keys.length - 1 && <span className={styles.then}> then </span>}
                    </span>
                  ))}
                </td>
                <td>{row.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
