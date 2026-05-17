import { useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { Header } from "./Header";
import { HelpOverlay } from "./HelpOverlay";
import { useKeyboardShortcuts } from "../hooks/useKeyboardShortcut";
import styles from "./Layout.module.css";

export function Layout() {
  const [helpOpen, setHelpOpen] = useState(false);
  const navigate = useNavigate();

  useKeyboardShortcuts([
    {
      key: "?",
      modifiers: ["shift"],
      handler: () => setHelpOpen(true),
    },
    {
      key: "Escape",
      handler: () => setHelpOpen(false),
      whenTyping: true,
    },
    {
      key: "g",
      handler: () => {
        // crude two-key sequence: after "g", listen once for "f" or "u".
        const onNext = (e: KeyboardEvent) => {
          if (e.key === "f") navigate("/");
          else if (e.key === "u") navigate("/users");
          window.removeEventListener("keydown", onNext);
        };
        window.addEventListener("keydown", onNext, { once: true });
      },
    },
  ]);

  return (
    <>
      <Header onOpenHelp={() => setHelpOpen(true)} />
      <main className={styles.main}>
        <Outlet />
      </main>
      <footer className={styles.footer}>
        <span>Press <kbd>?</kbd> for shortcuts</span>
      </footer>
      <HelpOverlay open={helpOpen} onClose={() => setHelpOpen(false)} />
    </>
  );
}
