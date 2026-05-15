import { useEffect, useState } from 'react'
import { useKeyboardShortcut } from '../../hooks/useKeyboardShortcut'

/**
 * Help overlay surfaced by pressing "?".
 * Lists every keyboard shortcut so the user can discover them without
 * dredging the README. Closes on Escape or backdrop click.
 *
 * This component renders globally inside AppShell so the shortcut is
 * available from every route.
 */
export function ShortcutOverlay() {
  const [open, setOpen] = useState(false)

  useKeyboardShortcut('?', () => setOpen((o) => !o))

  useEffect(() => {
    if (!open) return
    const onEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', onEsc)
    return () => window.removeEventListener('keydown', onEsc)
  }, [open])

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Show keyboard shortcuts"
        title="Press ? for keyboard shortcuts"
        style={hintBtn}
      >
        ?
      </button>
    )
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="kbd-title"
      onClick={() => setOpen(false)}
      style={backdrop}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={panel}
      >
        <h2 id="kbd-title" style={title}>
          Keyboard shortcuts
        </h2>
        <dl style={list}>
          <Row k="/" desc="Focus the search field on the Wall" />
          <Row k="?" desc="Open this overlay" />
          <Row k="⌘ + Enter" desc="Post / Reply when the composer is focused" />
          <Row k="Esc" desc="Close this overlay" />
        </dl>
        <p style={hint}>
          Press <span style={kbd}>?</span> or click outside to close.
        </p>
      </div>
    </div>
  )
}

function Row({ k, desc }: { k: string; desc: string }) {
  return (
    <div style={row}>
      <dt style={dt}>
        <span style={kbd}>{k}</span>
      </dt>
      <dd style={dd}>{desc}</dd>
    </div>
  )
}

const hintBtn: React.CSSProperties = {
  position: 'fixed',
  right: 24,
  bottom: 24,
  width: 32,
  height: 32,
  borderRadius: '50%',
  background: 'var(--cream)',
  border: '1px solid var(--gold)',
  color: 'var(--gold)',
  fontFamily: 'var(--font-sans)',
  fontSize: 14,
  fontWeight: 500,
  cursor: 'pointer',
  zIndex: 100,
}

const backdrop: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(15, 14, 12, 0.4)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 200,
  animation: 'kbdFadeIn 150ms ease-out',
}

const panel: React.CSSProperties = {
  background: 'var(--cream)',
  border: '1px solid var(--gold)',
  padding: '32px 36px',
  maxWidth: 420,
  width: '90%',
  boxShadow: '0 0 0 1px var(--gold-tint)',
}

const title: React.CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 11,
  letterSpacing: '0.22em',
  textTransform: 'uppercase',
  color: 'var(--black)',
  fontWeight: 500,
  paddingBottom: 14,
  borderBottom: '2px solid var(--black)',
  marginBottom: 20,
}

const list: React.CSSProperties = { margin: 0 }
const row: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '90px 1fr',
  alignItems: 'baseline',
  gap: 16,
  padding: '10px 0',
  borderBottom: '1px solid var(--hairline)',
}
const dt: React.CSSProperties = { margin: 0 }
const dd: React.CSSProperties = {
  margin: 0,
  fontFamily: 'var(--font-serif)',
  fontSize: 15,
  lineHeight: 1.4,
  color: 'var(--black)',
}
const kbd: React.CSSProperties = {
  display: 'inline-block',
  fontFamily: 'var(--font-sans)',
  fontSize: 11,
  letterSpacing: '0.1em',
  textTransform: 'uppercase',
  color: 'var(--gold)',
  border: '1px solid var(--gold)',
  padding: '2px 8px',
  background: 'var(--white)',
}

const hint: React.CSSProperties = {
  marginTop: 18,
  fontFamily: 'var(--font-serif)',
  fontStyle: 'italic',
  fontSize: 13,
  color: 'var(--muted)',
}
