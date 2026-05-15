/**
 * The thesis lives on every page so a viewer who never opens the README
 * still reads the design's argument.
 */
export function FooterThesis() {
  return (
    <footer
      style={{
        textAlign: 'center',
        padding: '28px 24px 48px',
        fontFamily: 'var(--font-serif)',
        fontStyle: 'italic',
        fontSize: 13,
        color: 'var(--muted)',
        borderTop: '1px solid var(--gold)',
        margin: '0 48px',
      }}
    >
      <em>A UATX Student Production. An online directory.</em>{' '}
      <span
        style={{
          fontFamily: 'var(--font-sans)',
          fontStyle: 'normal',
          textTransform: 'uppercase',
          letterSpacing: '0.18em',
          fontSize: 10,
          color: 'var(--black)',
          marginLeft: 4,
        }}
      >
        Not a feed
      </span>
    </footer>
  )
}
