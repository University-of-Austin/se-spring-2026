import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div style={{ maxWidth: 580, margin: '0 auto', padding: '48px 24px' }}>
      <p
        style={{
          fontFamily: 'var(--font-sans)',
          fontSize: 11,
          letterSpacing: '0.16em',
          textTransform: 'uppercase',
          color: 'var(--muted)',
          marginBottom: 14,
        }}
      >
        404 · Not in the Network
      </p>
      <h1
        style={{
          fontFamily: 'var(--font-serif)',
          fontSize: 32,
          fontWeight: 500,
          lineHeight: 1.1,
          marginBottom: 24,
        }}
      >
        That page is not in the directory.
      </h1>
      <p style={{ fontFamily: 'var(--font-serif)', fontSize: 17, lineHeight: 1.55 }}>
        Maybe the post was deleted, maybe the URL was wrong.{' '}
        <Link to="/" style={{ color: 'var(--gold)' }}>
          Return to the Wall
        </Link>
        .
      </p>
    </div>
  )
}
