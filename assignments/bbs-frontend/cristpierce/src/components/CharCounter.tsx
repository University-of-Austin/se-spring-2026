import styles from './CharCounter.module.css'

interface CharCounterProps {
  value: number
  max: number
}

export function CharCounter({ value, max }: CharCounterProps) {
  const over = value > max
  const near = !over && value > max * 0.9
  return (
    <span
      className={`${styles.counter} ${over ? styles.over : near ? styles.near : ''}`}
      aria-live="polite"
    >
      {value}/{max}
    </span>
  )
}
