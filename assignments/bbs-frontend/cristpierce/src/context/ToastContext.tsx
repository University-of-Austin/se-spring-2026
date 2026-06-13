/* eslint-disable react-refresh/only-export-components -- Provider + hook
   intentionally colocated. */

/*
 * Transient toast notifications. These are the visible half of optimistic
 * updates: when a post/delete/reaction is rolled back, the user sees a toast
 * explaining why instead of silently losing their action.
 */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from 'react'
import type { ReactNode } from 'react'

export type ToastKind = 'error' | 'success' | 'info'

export interface Toast {
  id: number
  message: string
  kind: ToastKind
}

interface ToastValue {
  toasts: Toast[]
  push: (message: string, kind?: ToastKind) => void
  error: (message: string) => void
  success: (message: string) => void
  info: (message: string) => void
  dismiss: (id: number) => void
}

const ToastContext = createContext<ToastValue | null>(null)
const AUTO_DISMISS_MS = 5_000

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const nextId = useRef(1)

  const dismiss = useCallback((id: number) => {
    setToasts((list) => list.filter((t) => t.id !== id))
  }, [])

  const push = useCallback(
    (message: string, kind: ToastKind = 'info') => {
      const id = nextId.current++
      setToasts((list) => [...list, { id, message, kind }])
      window.setTimeout(() => dismiss(id), AUTO_DISMISS_MS)
    },
    [dismiss],
  )

  const error = useCallback((message: string) => push(message, 'error'), [push])
  const success = useCallback((message: string) => push(message, 'success'), [push])
  const info = useCallback((message: string) => push(message, 'info'), [push])

  const value = useMemo<ToastValue>(
    () => ({ toasts, push, error, success, info, dismiss }),
    [toasts, push, error, success, info, dismiss],
  )

  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>
}

export function useToast(): ToastValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within a ToastProvider')
  return ctx
}
