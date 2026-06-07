import { useEffect, useState } from 'react'

/**
 * Live indicator dot in the masthead. Pulses when the tab is visible
 * (polling is on); goes dim when the tab is hidden (polling paused).
 * aria-live="polite" so screen readers announce status changes.
 */
export function LiveDot() {
  const [visible, setVisible] = useState(() =>
    typeof document === 'undefined' ? true : document.visibilityState === 'visible',
  )

  useEffect(() => {
    const onChange = () => setVisible(document.visibilityState === 'visible')
    document.addEventListener('visibilitychange', onChange)
    return () => document.removeEventListener('visibilitychange', onChange)
  }, [])

  return (
    <span
      role="status"
      aria-live="polite"
      aria-label={visible ? 'Live updates on' : 'Live updates paused'}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        fontFamily: 'var(--font-sans)',
        fontSize: 10,
        letterSpacing: '0.18em',
        textTransform: 'uppercase',
        color: visible ? 'var(--white)' : 'rgba(255,255,255,0.55)',
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: visible ? '#fff' : 'rgba(255,255,255,0.45)',
          animation: visible ? 'liveDotPulse 1.6s ease-in-out infinite' : 'none',
        }}
      />
      <style>{`
        @keyframes liveDotPulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%      { opacity: 0.45; transform: scale(0.85); }
        }
      `}</style>
      Live
    </span>
  )
}
