import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getUser, getUserPosts } from '../api/users'
import { ApiError } from '../api/types'
import { useIdentity } from '../auth/useIdentity'
import { PostCard } from '../components/feed/PostCard'
import { BioEditor } from '../components/profile/BioEditor'
import { LoadingRow, ErrorBanner, EmptyState } from '../components/states/States'
import { formatRelative } from '../lib/formatTime'

export default function UserProfilePage() {
  const { username = '' } = useParams<{ username: string }>()
  const { username: viewer } = useIdentity()
  const isOwn = viewer && username && viewer === username

  const userQ = useQuery({
    queryKey: ['user', username],
    queryFn: () => getUser(username),
    retry: (failureCount, err) => {
      if (err instanceof ApiError && err.status === 404) return false
      return failureCount < 1
    },
  })

  const postsQ = useQuery({
    queryKey: ['user', username, 'posts'],
    queryFn: () => getUserPosts(username, 50, 0),
    enabled: userQ.isSuccess,
  })
  const userPosts = postsQ.data ?? []

  // 404 view
  if (userQ.isError && userQ.error instanceof ApiError && userQ.error.status === 404) {
    return (
      <div style={{ maxWidth: 580, margin: '0 auto', padding: '48px 24px' }}>
        <p
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize: 11,
            letterSpacing: '0.18em',
            textTransform: 'uppercase',
            color: 'var(--muted)',
            marginBottom: 12,
          }}
        >
          404 · Not in the Directory
        </p>
        <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 32, fontWeight: 500, lineHeight: 1.1, marginBottom: 16 }}>
          @{username} is not in the Network.
        </h1>
        <p style={{ fontFamily: 'var(--font-serif)', fontSize: 17, lineHeight: 1.55 }}>
          <Link to="/users" style={{ color: 'var(--gold)' }}>Back to the Directory →</Link>
        </p>
      </div>
    )
  }

  return (
    <div style={wrap} data-shell="two-col">
      <main>
        {userQ.isLoading ? <LoadingRow label="Profile" /> : null}
        {userQ.isError && !(userQ.error instanceof ApiError && userQ.error.status === 404) ? (
          <ErrorBanner error={userQ.error} onRetry={() => void userQ.refetch()} />
        ) : null}

        {userQ.data ? (
          <>
            <header style={{ marginBottom: 32, paddingBottom: 14, borderBottom: '2px solid var(--black)' }}>
              <p style={eyebrow}>Profile · joined {formatRelative(userQ.data.created_at)}</p>
              <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 36, fontWeight: 500, lineHeight: 1.1 }}>
                @{userQ.data.username}
              </h1>
              {isOwn ? (
                <BioEditor user={userQ.data} />
              ) : userQ.data.bio ? (
                <p style={{ marginTop: 12, fontFamily: 'var(--font-serif)', fontSize: 17, lineHeight: 1.5 }}>
                  {userQ.data.bio}
                </p>
              ) : null}
            </header>

            <h2 style={eyebrow}>
              The Wall · {userQ.data.post_count} {userQ.data.post_count === 1 ? 'post' : 'posts'}
            </h2>

            {postsQ.isLoading ? <LoadingRow label="Posts" /> : null}
            {postsQ.isError ? (
              <ErrorBanner error={postsQ.error} onRetry={() => void postsQ.refetch()} />
            ) : null}
            {postsQ.data && userPosts.length === 0 ? (
              <EmptyState title="No posts yet" />
            ) : null}
            {userPosts.map((p, i) => <PostCard key={p.id} post={p} isFirst={i === 0} />)}
          </>
        ) : null}
      </main>

      <aside>
        <section style={{ marginBottom: 32 }}>
          <h2 style={sideH}>Stats</h2>
          <div style={statNum}>{userQ.data?.post_count ?? '—'}</div>
          <div style={statSub}>posts in the directory</div>
        </section>
      </aside>
    </div>
  )
}

const wrap: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '580px 200px',
  gap: 48,
  maxWidth: 860,
  margin: '0 auto',
  padding: '48px 24px 56px',
}

const eyebrow: React.CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 11,
  letterSpacing: '0.18em',
  textTransform: 'uppercase',
  color: 'var(--muted)',
  marginBottom: 14,
}

const sideH: React.CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 10,
  letterSpacing: '0.2em',
  textTransform: 'uppercase',
  color: 'var(--black)',
  paddingBottom: 6,
  borderBottom: '1px solid var(--gold)',
  marginBottom: 14,
  fontWeight: 500,
}

const statNum: React.CSSProperties = {
  fontFamily: 'var(--font-serif)',
  fontSize: 40,
  lineHeight: 1,
  color: 'var(--black)',
}

const statSub: React.CSSProperties = {
  fontFamily: 'var(--font-serif)',
  fontStyle: 'italic',
  fontSize: 13,
  color: 'var(--muted)',
  marginTop: 4,
}
