import { Modal } from './ui/Modal'
import { SHORTCUTS } from '../hooks/useKeyboard'
import styles from './ShortcutsOverlay.module.css'

interface ShortcutsOverlayProps {
  open: boolean
  onClose: () => void
}

export function ShortcutsOverlay({ open, onClose }: ShortcutsOverlayProps) {
  return (
    <Modal open={open} onClose={onClose} title="Keyboard shortcuts">
      <ul className={styles.list}>
        {SHORTCUTS.map((s) => (
          <li key={s.label} className={styles.row}>
            <kbd className={styles.kbd}>{s.keys}</kbd>
            <span className={styles.label}>{s.label}</span>
          </li>
        ))}
      </ul>
    </Modal>
  )
}
