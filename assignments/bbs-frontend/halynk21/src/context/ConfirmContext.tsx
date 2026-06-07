import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';

export type ConfirmOptions = {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
};

type ConfirmContextValue = {
  confirm: (opts: ConfirmOptions) => Promise<boolean>;
};

const ConfirmContext = createContext<ConfirmContextValue | null>(null);

type DialogState = {
  options: ConfirmOptions;
  resolve: (ok: boolean) => void;
};

export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<DialogState | null>(null);
  const confirmBtnRef = useRef<HTMLButtonElement | null>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  const confirm = useCallback((options: ConfirmOptions): Promise<boolean> => {
    return new Promise<boolean>((resolve) => {
      setState({ options, resolve });
    });
  }, []);

  const close = useCallback(
    (ok: boolean) => {
      state?.resolve(ok);
      setState(null);
    },
    [state],
  );

  // Esc to cancel, autofocus the confirm button on open, and on close
  // restore focus to whatever was focused before the dialog opened — so
  // a keyboard user doesn't get dumped onto <body>.
  useEffect(() => {
    if (!state) return;
    previousFocusRef.current = document.activeElement as HTMLElement | null;
    confirmBtnRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close(false);
    };
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      previousFocusRef.current?.focus();
    };
  }, [state, close]);

  return (
    <ConfirmContext.Provider value={{ confirm }}>
      {children}
      {state && (
        <div
          className="dialog-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-title"
          onClick={(e) => {
            if (e.target === e.currentTarget) close(false);
          }}
        >
          <div className="dialog">
            <h2 id="confirm-title">{state.options.title}</h2>
            <p style={{ marginTop: 'var(--space-2)', color: 'var(--fg-muted)' }}>
              {state.options.message}
            </p>
            <div className="dialog-actions">
              <button
                type="button"
                className="btn btn--ghost"
                onClick={() => close(false)}
              >
                {state.options.cancelLabel ?? 'Cancel'}
              </button>
              <button
                type="button"
                ref={confirmBtnRef}
                className={state.options.destructive ? 'btn btn--danger' : 'btn btn--primary'}
                onClick={() => close(true)}
              >
                {state.options.confirmLabel ?? 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useConfirm(): ConfirmContextValue['confirm'] {
  const v = useContext(ConfirmContext);
  if (!v) throw new Error('useConfirm must be used inside <ConfirmProvider>');
  return v.confirm;
}
