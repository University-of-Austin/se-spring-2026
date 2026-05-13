import { useCallback, useState } from "react";
import type { ToastMessage } from "../components/Toast";

let toastCounter = 0;

export function useToasts() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const push = useCallback(
    (text: string, kind: ToastMessage["kind"] = "info") => {
      toastCounter += 1;
      setToasts((prev) => [...prev, { id: toastCounter, text, kind }]);
    },
    []
  );

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return { toasts, push, dismiss };
}
