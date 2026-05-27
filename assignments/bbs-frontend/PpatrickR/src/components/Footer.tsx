export function Footer() {
  return (
    <footer className="app-footer" aria-label="Keyboard shortcuts">
      <span>Shortcuts:</span>
      <kbd>/</kbd>
      <span className="muted small">focus search</span>
      <span className="sep" aria-hidden="true">
        ·
      </span>
      <kbd>n</kbd>
      <span className="muted small">new post</span>
      <span className="sep" aria-hidden="true">
        ·
      </span>
      <kbd>Cmd</kbd>
      <span aria-hidden="true">/</span>
      <kbd>Ctrl</kbd>
      <span className="muted small">+</span>
      <kbd>Enter</kbd>
      <span className="muted small">post (in compose)</span>
    </footer>
  );
}
