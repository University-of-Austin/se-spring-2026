import { useEffect } from "react";

export interface ToastMessage {
  id: number;
  text: string;
  kind?: "info" | "danger";
}

export function ToastRow({
  toasts,
  onDismiss,
}: {
  toasts: ToastMessage[];
  onDismiss: (id: number) => void;
}) {
  return (
    <div className="toast-row" aria-live="polite" aria-atomic="false">
      {toasts.map((t) => (
        <Toast key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

function Toast({
  toast,
  onDismiss,
}: {
  toast: ToastMessage;
  onDismiss: (id: number) => void;
}) {
  useEffect(() => {
    const t = window.setTimeout(() => onDismiss(toast.id), 4000);
    return () => window.clearTimeout(t);
  }, [toast.id, onDismiss]);

  return (
    <div className={`toast${toast.kind === "danger" ? " danger" : ""}`} role="status">
      {toast.text}
    </div>
  );
}
