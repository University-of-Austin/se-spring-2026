import { useToast } from '../../context/ToastContext'
import { CloseIcon } from './icons'
import styles from './Toaster.module.css'

/** Renders the toast stack. Mounted once, near the root. */
export function Toaster() {
  const { toasts, dismiss } = useToast()
  if (toasts.length === 0) return null

  return (
    <div className={styles.region} role="region" aria-label="Notifications">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`${styles.toast} ${styles[t.kind]}`}
          role={t.kind === 'error' ? 'alert' : 'status'}
        >
          <span className={styles.msg}>{t.message}</span>
          <button
            type="button"
            className={styles.close}
            aria-label="Dismiss notification"
            onClick={() => dismiss(t.id)}
          >
            <CloseIcon size={15} />
          </button>
        </div>
      ))}
    </div>
  )
}
