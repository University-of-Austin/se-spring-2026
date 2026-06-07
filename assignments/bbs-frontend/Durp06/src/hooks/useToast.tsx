import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';

interface ToastMsg {
  id: number;
  kind: 'error' | 'info';
  text: string;
}

interface ToastValue {
  toasts: ToastMsg[];
  push: (text: string, kind?: 'error' | 'info') => void;
  dismiss: (id: number) => void;
}

const ToastCtx = createContext<ToastValue | null>(null);

let _id = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMsg[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((cur) => cur.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (text: string, kind: 'error' | 'info' = 'info') => {
      const id = ++_id;
      setToasts((cur) => [...cur, { id, kind, text }]);
      // Auto-dismiss after 5s.
      window.setTimeout(() => dismiss(id), 5000);
    },
    [dismiss],
  );

  return <ToastCtx.Provider value={{ toasts, push, dismiss }}>{children}</ToastCtx.Provider>;
}

export function useToast(): ToastValue {
  const v = useContext(ToastCtx);
  if (!v) throw new Error('useToast must be used inside <ToastProvider>');
  return v;
}

// Renders toasts. Lives separately so any provider tree can mount it without
// dragging in markup-coupling.
export function ToastTray() {
  const { toasts, dismiss } = useToast();
  useEffect(() => {
    // no-op; effect kept for future global handling
  }, []);
  return (
    <div className="toast-tray" aria-live="polite" aria-atomic="false">
      {toasts.map((t) => (
        <div key={t.id} role="alert" className={`toast toast--${t.kind}`}>
          <span>{t.text}</span>
          <button type="button" onClick={() => dismiss(t.id)} aria-label="Dismiss notification">
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
