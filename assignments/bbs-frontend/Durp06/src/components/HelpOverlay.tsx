import { useEffect } from 'react';

interface Props {
  open: boolean;
  onClose: () => void;
}

const SHORTCUTS: { keys: string; description: string }[] = [
  { keys: '?', description: 'Toggle this help' },
  { keys: 'g f', description: 'Go to feed' },
  { keys: 'g u', description: 'Go to users' },
  { keys: 'n', description: 'New post (focus compose)' },
  { keys: 't', description: 'Toggle light / dark theme' },
  { keys: 'Ctrl / ⌘ + Enter', description: 'Submit compose form' },
];

export function HelpOverlay({ open, onClose }: Props) {
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
    <div className="overlay" role="dialog" aria-modal="true" aria-labelledby="help-title" onClick={onClose}>
      <div className="overlay__panel" onClick={(e) => e.stopPropagation()}>
        <header className="overlay__header">
          <h2 id="help-title">Keyboard shortcuts</h2>
          <button type="button" className="btn btn--ghost" onClick={onClose} aria-label="Close help">
            ×
          </button>
        </header>
        <dl className="shortcuts">
          {SHORTCUTS.map((s) => (
            <div key={s.keys} className="shortcuts__row">
              <dt>
                <kbd>{s.keys}</kbd>
              </dt>
              <dd>{s.description}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
