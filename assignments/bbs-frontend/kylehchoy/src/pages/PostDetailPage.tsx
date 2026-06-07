import { useParams, useNavigate, Link } from 'react-router-dom'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getPostWithEtag, invalidatePostEtag, deletePost } from '../api/posts'
import type { Post } from '../api/types'
import { ApiError } from '../api/types'
import { useIdentity } from '../auth/useIdentity'
import { LoadingRow, ErrorBanner } from '../components/states/States'
import { ReactionBar } from '../components/reactions/ReactionBar'
import { ReplyTree } from '../components/thread/ReplyTree'
import { PostEditor } from '../components/post/PostEditor'
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
  // All hook calls must be unconditional; do not move below the 404
  // early return. React's hook contract requires identical call order
  // on every render, and a 404 response toggles whether we return early.
  const [confirming, setConfirming] = useState(false)
  const [editing, setEditing] = useState(false)

  /**
   * Conditional GET via A2's weak ETag on /posts/{id}. The first call
   * carries no If-None-Match; the second sends the previously-seen
   * ETag. If the post is unchanged, A2 returns 304 (notModified=true)
   * and we keep the cached Post — saves the JSON body over the wire.
   *
   * TanStack Query's structural sharing means even a successful 200
   * with identical content won't trigger re-renders; the 304 just
   * saves bandwidth (and a JSON parse).
   */
  const postQ = useQuery<Post>({
    queryKey: ['post', postId],
    queryFn: async () => {
      const result = await getPostWithEtag(postId)
      if (result.notModified) {
        // Use cached data. Query will accept the previousData if we
        // return it explicitly.
        const cached = qc.getQueryData<Post>(['post', postId])
        if (cached) return cached
        // 304 + no cache means our ETag is stale relative to Query's GC.
        // Force a non-conditional fetch by clearing the stored ETag and
        // re-asking. The retry won't send If-None-Match this time.
        invalidatePostEtag(postId)
        const fresh = await getPostWithEtag(postId)
        if (fresh.data) return fresh.data
        throw new ApiError(0, 'Empty response after 304', 'Failed to refetch post.')
      }
      return result.data
    },
    retry: (n, err) => !(err instanceof ApiError && err.status === 404) && n < 1,
    enabled: Number.isFinite(postId),
  })

  const deleteMut = useMutation({
    mutationFn: () => deletePost(postId),
    onSuccess: () => {
      // Tear down every cache entry that referenced the deleted post.
      // Without this, staleTime: 30_000 (queryClient.ts) keeps the
      // ghost row around — revisiting /posts/:id within 30s would show
      // the deleted content because Query treats the cache as fresh.
      qc.removeQueries({ queryKey: ['post', postId] })
      qc.removeQueries({ queryKey: ['post', postId, 'replies'] })
      qc.removeQueries({ queryKey: ['post', postId, 'reactions'] })
      invalidatePostEtag(postId)
      qc.invalidateQueries({ queryKey: ['posts'] })
      qc.invalidateQueries({ queryKey: ['user'] })
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
            {post.updated_at && post.updated_at !== post.created_at ? (
              <>
                <span style={{ color: 'var(--gold)', margin: '0 6px' }}>·</span>
                <span style={{ fontStyle: 'italic', textTransform: 'none', letterSpacing: 'normal', fontFamily: 'var(--font-serif)', fontSize: 13 }}>
                  edited {formatRelative(post.updated_at)}
                </span>
              </>
            ) : null}
          </p>

          {editing ? (
            <PostEditor post={post} onDone={() => setEditing(false)} />
          ) : (
            <>
              <div style={{ fontFamily: 'var(--font-serif)', fontSize: 19, lineHeight: 1.6, color: 'var(--black)' }}>
                {post.message.split(/\n\s*\n/).map((p, i) => (
                  <p key={i} style={{ marginTop: i === 0 ? 0 : '0.6em' }}>{p}</p>
                ))}
              </div>

              <ReactionBar post={post} />

              {isAuthor ? (
                <div style={{ marginTop: 24, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    onClick={() => setEditing(true)}
                    style={{
                      fontFamily: 'var(--font-sans)',
                      fontSize: 10,
                      letterSpacing: '0.18em',
                      textTransform: 'uppercase',
                      color: 'var(--gold)',
                      background: 'transparent',
                      border: '1px solid var(--gold)',
                      padding: '6px 14px',
                      cursor: 'pointer',
                    }}
                  >
                    Edit post
                  </button>
                  <button
                    type="button"
                    onClick={onDelete}
                    disabled={deleteMut.isPending}
                    style={{
                      fontFamily: 'var(--font-sans)',
                      fontSize: 10,
                      letterSpacing: '0.18em',
                      textTransform: 'uppercase',
                      color: confirming ? '#b34a3a' : 'var(--muted)',
                      background: 'transparent',
                      border: `1px solid ${confirming ? '#b34a3a' : 'var(--hairline)'}`,
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
                    <div style={{ marginTop: 16, width: '100%' }}>
                      <ErrorBanner error={deleteMut.error} />
                    </div>
                  ) : null}
                </div>
              ) : null}
            </>
          )}
        </article>
      ) : null}

      {post ? <ReplyTree rootId={post.id} /> : null}
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
