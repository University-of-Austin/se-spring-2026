import { createContext, useCallback, useContext, useRef, useState } from 'react';

export type ToastSeverity = 'info' | 'success' | 'error';

type Toast = {
  id: number;
  severity: ToastSeverity;
  message: string;
};

type ToastContextValue = {
  toast: (severity: ToastSeverity, message: string) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

const AUTO_DISMISS_MS = 4000;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextIdRef = useRef<number>(1);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (severity: ToastSeverity, message: string) => {
      const id = nextIdRef.current++;
      setToasts((prev) => [...prev, { id, severity, message }]);
      window.setTimeout(() => dismiss(id), AUTO_DISMISS_MS);
    },
    [dismiss],
  );

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="toast-region" role="status" aria-live="polite">
        {toasts.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`toast toast--${t.severity}`}
            onClick={() => dismiss(t.id)}
            aria-label={`${t.severity}: ${t.message}. Click to dismiss.`}
          >
            {t.message}
          </button>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useToast(): ToastContextValue {
  const v = useContext(ToastContext);
  if (!v) throw new Error('useToast must be used inside <ToastProvider>');
  return v;
}
