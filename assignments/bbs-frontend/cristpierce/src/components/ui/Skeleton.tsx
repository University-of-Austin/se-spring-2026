import styles from './Skeleton.module.css'

interface SkeletonProps {
  width?: string
  height?: string
  className?: string
}

export function Skeleton({ width, height = '1em', className }: SkeletonProps) {
  return (
    <span
      className={`${styles.skeleton} ${className ?? ''}`}
      style={{ width, height }}
      aria-hidden="true"
    />
  )
}

/** A skeleton placeholder shaped like a PostCard, shown while the feed loads. */
export function PostCardSkeleton() {
  return (
    <div className={styles.card} aria-hidden="true">
      <div className={styles.row}>
        <Skeleton width="34px" height="34px" className={styles.avatar} />
        <div className={styles.meta}>
          <Skeleton width="120px" height="0.85em" />
          <Skeleton width="60px" height="0.7em" />
        </div>
      </div>
      <Skeleton width="92%" height="0.9em" />
      <Skeleton width="70%" height="0.9em" />
    </div>
  )
}
