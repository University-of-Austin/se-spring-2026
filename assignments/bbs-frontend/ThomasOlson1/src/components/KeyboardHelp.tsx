import { useEffect, useState } from "react";

const SHORTCUTS = [
  { keys: "⌘/Ctrl + Enter", desc: "Submit a post from the compose box" },
  { keys: "/", desc: "Focus the feed search input" },
  { keys: "g + h", desc: "Go to feed (home)" },
  { keys: "g + u", desc: "Go to user list" },
  { keys: "g + s", desc: "Go to sign in / switch user" },
  { keys: "t", desc: "Toggle light / dark theme" },
  { keys: "?", desc: "Show / hide this shortcuts panel" },
];

export function KeyboardHelp({
  onNavigate,
  onToggleTheme,
  onFocusSearch,
}: {
  onNavigate: (path: string) => void;
  onToggleTheme: () => void;
  onFocusSearch: () => void;
}) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let gPressed = false;
    let gTimer: number | undefined;

    function isTypingTarget(t: EventTarget | null) {
      const el = t as HTMLElement | null;
      if (!el) return false;
      const tag = el.tagName;
      return tag === "INPUT" || tag === "TEXTAREA" || (el as HTMLElement).isContentEditable;
    }

    function onKey(e: KeyboardEvent) {
      if (e.key === "?" && !isTypingTarget(e.target)) {
        e.preventDefault();
        setOpen((v) => !v);
        return;
      }
      if (e.key === "Escape") {
        setOpen(false);
        return;
      }
      if (isTypingTarget(e.target)) return;

      if (e.key === "/") {
        e.preventDefault();
        onFocusSearch();
        return;
      }
      if (e.key === "t") {
        onToggleTheme();
        return;
      }
      if (e.key === "g") {
        gPressed = true;
        window.clearTimeout(gTimer);
        gTimer = window.setTimeout(() => (gPressed = false), 1000);
        return;
      }
      if (gPressed) {
        gPressed = false;
        if (e.key === "h") onNavigate("/");
        else if (e.key === "u") onNavigate("/users");
        else if (e.key === "s") onNavigate("/signup");
      }
    }
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.clearTimeout(gTimer);
    };
  }, [onNavigate, onToggleTheme, onFocusSearch]);

  return (
    <>
      <button
        type="button"
        className="kb-help-btn"
        aria-label="Show keyboard shortcuts"
        onClick={() => setOpen((v) => !v)}
      >
        ?
      </button>
      {open && (
        <div
          className="kb-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="kb-title"
          onClick={() => setOpen(false)}
        >
          <div className="kb-panel" onClick={(e) => e.stopPropagation()}>
            <h2 id="kb-title">Keyboard shortcuts</h2>
            <table>
              <tbody>
                {SHORTCUTS.map((s) => (
                  <tr key={s.keys}>
                    <th scope="row">
                      <kbd>{s.keys}</kbd>
                    </th>
                    <td>{s.desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button type="button" className="btn" onClick={() => setOpen(false)}>
              Close (Esc)
            </button>
          </div>
        </div>
      )}
    </>
  );
}
