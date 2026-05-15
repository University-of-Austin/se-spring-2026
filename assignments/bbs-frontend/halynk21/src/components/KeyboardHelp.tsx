import { useEffect } from 'react';

const SHORTCUTS: Array<[string, string]> = [
  ['/', 'Focus the search box'],
  ['n', 'Go to feed and focus the compose box'],
  ['Cmd/Ctrl + Enter', 'Post the compose draft'],
  ['?', 'Show this help'],
  ['Esc', 'Close this help'],
];

export function KeyboardHelp({ open, onClose }: { open: boolean; onClose: () => void }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div
      className="dialog-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="kbd-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="help-overlay">
        <h2 id="kbd-title">Keyboard shortcuts</h2>
        <dl>
          {SHORTCUTS.map(([k, v]) => (
            <div key={k} style={{ display: 'contents' }}>
              <dt>{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
        <div className="dialog-actions">
          <button type="button" className="btn btn--ghost" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
