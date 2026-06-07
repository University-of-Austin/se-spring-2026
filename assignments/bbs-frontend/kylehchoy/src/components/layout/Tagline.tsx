/**
 * Italic serif tagline beneath the masthead.
 * Pulled verbatim from 2004 Facebook's own pitch: "an online directory that
 * connects people through social networks at colleges." We slot UATX in.
 */
export function Tagline() {
  return (
    <div
      style={{
        textAlign: 'center',
        padding: '18px 24px 6px',
        fontFamily: 'var(--font-serif)',
        fontStyle: 'italic',
        fontSize: 14,
        color: 'var(--muted)',
        borderBottom: '1px solid var(--hairline)',
        margin: '0 24px',
      }}
    >
      An online directory for the University of Austin community.
    </div>
  )
}
