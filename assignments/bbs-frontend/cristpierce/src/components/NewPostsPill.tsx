import styles from './NewPostsPill.module.css'

interface NewPostsPillProps {
  count: number
  onClick: () => void
}

/** The live-update affordance: appears when polling finds new posts, so the
 *  feed never yanks the user's scroll position out from under them. */
export function NewPostsPill({ count, onClick }: NewPostsPillProps) {
  if (count <= 0) return null
  return (
    <div className={styles.wrap}>
      <button type="button" className={styles.pill} onClick={onClick}>
        ↑ {count} new {count === 1 ? 'post' : 'posts'}
      </button>
    </div>
  )
}
