import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listUsers } from '../api/users'
import { LoadingRow, ErrorBanner, EmptyState } from '../components/states/States'

export default function UsersPage() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['users'],
    queryFn: () => listUsers(200, 0),
  })

  return (
    <div style={{ maxWidth: 580, margin: '0 auto', padding: '48px 24px 56px' }}>
      <header style={{ marginBottom: 32, paddingBottom: 14, borderBottom: '2px solid var(--black)' }}>
        <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 32, fontWeight: 500, lineHeight: 1.1 }}>
          The Directory
        </h1>
        <p
          style={{
            marginTop: 8,
            fontFamily: 'var(--font-sans)',
            fontSize: 11,
            letterSpacing: '0.18em',
            textTransform: 'uppercase',
            color: 'var(--muted)',
          }}
        >
          {data ? `${data.length} students in the Network` : 'Loading the roster…'}
        </p>
      </header>

      {isLoading ? <LoadingRow label="Directory" /> : null}
      {isError ? <ErrorBanner error={error} onRetry={() => void refetch()} /> : null}
      {!isLoading && !isError && data && data.length === 0 ? (
        <EmptyState title="No one's in the directory yet">
          <Link to="/signup" style={{ color: 'var(--gold)' }}>Be the first →</Link>
        </EmptyState>
      ) : null}

      <ul style={{ listStyle: 'none', padding: 0 }}>
        {data?.map((u) => (
          <li
            key={u.username}
            style={{
              padding: '20px 0',
              borderBottom: '1px solid var(--hairline)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'baseline',
              gap: 16,
            }}
          >
            <div>
              <Link
                to={`/users/${encodeURIComponent(u.username)}`}
                style={{
                  fontFamily: 'var(--font-serif)',
                  fontSize: 18,
                  fontWeight: 500,
                  color: 'var(--black)',
                  textDecoration: 'underline',
                  textUnderlineOffset: 3,
                }}
              >
                @{u.username}
              </Link>
              {u.bio ? (
                <p
                  style={{
                    marginTop: 4,
                    fontFamily: 'var(--font-serif)',
                    fontStyle: 'italic',
                    fontSize: 14,
                    color: 'var(--muted)',
                  }}
                >
                  {u.bio}
                </p>
              ) : null}
            </div>
            <span
              style={{
                fontFamily: 'var(--font-sans)',
                fontSize: 10,
                letterSpacing: '0.16em',
                textTransform: 'uppercase',
                color: 'var(--muted)',
                whiteSpace: 'nowrap',
              }}
            >
              {u.post_count} {u.post_count === 1 ? 'post' : 'posts'}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
