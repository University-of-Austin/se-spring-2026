import { useParams, useNavigate, Link } from 'react-router-dom'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getPost, deletePost } from '../api/posts'
import { ApiError } from '../api/types'
import { useIdentity } from '../auth/IdentityContext'
import { LoadingRow, ErrorBanner } from '../components/states/States'
import { ReactionBar } from '../components/reactions/ReactionBar'
import { formatRelative } from '../lib/formatTime'

/**
 * Phase 3: post detail + delete + back-link.
 * Phase 7 expands this into the full Live Thread (reply tree, optimistic
 * inserts, polled arrivals, reactions). For now, the basic surface.
 */
export default function PostDetailPage() {
  const { id = '' } = useParams<{ id: string }>()
  const postId = Number(id)
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { username } = useIdentity()
  const [confirming, setConfirming] = useState(false)

  const postQ = useQuery({
    queryKey: ['post', postId],
    queryFn: () => getPost(postId),
    retry: (n, err) => !(err instanceof ApiError && err.status === 404) && n < 1,
    enabled: Number.isFinite(postId),
  })

  const deleteMut = useMutation({
    mutationFn: () => deletePost(postId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['posts'] })
      navigate('/', { replace: true })
    },
  })

  if (postQ.isError && postQ.error instanceof ApiError && postQ.error.status === 404) {
    return (
      <div style={{ maxWidth: 580, margin: '0 auto', padding: '48px 24px' }}>
        <p style={eyebrow}>404 · Thread not in the Directory</p>
        <h1 style={{ fontFamily: 'var(--font-serif)', fontSize: 32, fontWeight: 500, lineHeight: 1.1, marginBottom: 16 }}>
          That post is gone.
        </h1>
        <p style={{ fontFamily: 'var(--font-serif)', fontSize: 17, lineHeight: 1.55 }}>
          Maybe the author deleted it. <Link to="/" style={{ color: 'var(--gold)' }}>Back to the Wall →</Link>
        </p>
      </div>
    )
  }

  const post = postQ.data
  const isAuthor = post && username && post.username === username
  const onDelete = () => {
    if (!confirming) {
      setConfirming(true)
      return
    }
    deleteMut.mutate()
  }

  return (
    <div style={{ maxWidth: 580, margin: '0 auto', padding: '48px 24px 56px' }}>
      <p style={eyebrow}>
        <Link to="/" style={{ color: 'inherit', textDecoration: 'none' }}>← Back to the Wall</Link>
      </p>

      {postQ.isLoading ? <LoadingRow label="Thread" /> : null}
      {postQ.isError ? <ErrorBanner error={postQ.error} onRetry={() => void postQ.refetch()} /> : null}

      {post ? (
        <article style={{ paddingBottom: 32, marginBottom: 32, borderBottom: '1px solid var(--gold)' }}>
          <p style={eyebrow}>
            <span>Wall</span>
            <span style={{ color: 'var(--gold)', margin: '0 6px' }}>·</span>
            <span>{formatRelative(post.created_at)}</span>
            <span style={{ color: 'var(--gold)', margin: '0 6px' }}>·</span>
            <Link
              to={`/users/${encodeURIComponent(post.username)}`}
              style={{ color: 'var(--black)', fontWeight: 500 }}
            >
              @{post.username}
            </Link>
            <span style={{ color: 'var(--gold)', margin: '0 6px' }}>·</span>
            <span>№ {post.id}</span>
          </p>

          <div style={{ fontFamily: 'var(--font-serif)', fontSize: 19, lineHeight: 1.6, color: 'var(--black)' }}>
            {post.message.split(/\n\s*\n/).map((p, i) => (
              <p key={i} style={{ marginTop: i === 0 ? 0 : '0.6em' }}>{p}</p>
            ))}
          </div>

          <ReactionBar post={post} />

          {isAuthor ? (
            <div style={{ marginTop: 24 }}>
              <button
                type="button"
                onClick={onDelete}
                disabled={deleteMut.isPending}
                style={{
                  fontFamily: 'var(--font-sans)',
                  fontSize: 10,
                  letterSpacing: '0.18em',
                  textTransform: 'uppercase',
                  color: confirming ? '#b34a3a' : 'var(--gold)',
                  background: 'transparent',
                  border: `1px solid ${confirming ? '#b34a3a' : 'var(--gold)'}`,
                  padding: '6px 14px',
                  cursor: 'pointer',
                }}
              >
                {deleteMut.isPending
                  ? 'Deleting…'
                  : confirming
                    ? 'Click again to confirm delete'
                    : 'Delete post'}
              </button>
              {confirming ? (
                <button
                  type="button"
                  onClick={() => setConfirming(false)}
                  style={{
                    marginLeft: 12,
                    fontFamily: 'var(--font-sans)',
                    fontSize: 10,
                    letterSpacing: '0.18em',
                    textTransform: 'uppercase',
                    color: 'var(--muted)',
                    background: 'transparent',
                    border: 0,
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
              ) : null}
              {deleteMut.isError ? (
                <div style={{ marginTop: 16 }}>
                  <ErrorBanner error={deleteMut.error} />
                </div>
              ) : null}
            </div>
          ) : null}
        </article>
      ) : null}

      <p style={{ fontFamily: 'var(--font-serif)', fontStyle: 'italic', fontSize: 14, color: 'var(--muted)' }}>
        Replies, reactions, and the live thread experience arrive in the next build pass.
      </p>
    </div>
  )
}

const eyebrow: React.CSSProperties = {
  fontFamily: 'var(--font-sans)',
  fontSize: 11,
  letterSpacing: '0.18em',
  textTransform: 'uppercase',
  color: 'var(--muted)',
  marginBottom: 14,
}
