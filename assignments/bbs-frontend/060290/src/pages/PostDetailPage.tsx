import { useCallback } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import { bbsApi } from '../api/bbs'
import { FetchStateDisplay } from '../components/FetchStateDisplay'
import { useMountFetch } from '../hooks/useMountFetch'
import { useMutation } from '../hooks/useMutation'
import { ServerValidationErrors } from '../components/ServerValidationErrors'
import './pages.css'

export function PostDetailPage() {
  const { id: rawId } = useParams()
  const postId = Number(rawId)
  const invalid = !rawId || !Number.isInteger(postId) || postId < 1

  const { state, refetch } = useMountFetch(
    `post-detail:${rawId}:${invalid ? 'x' : 'ok'}`,
    () => {
      if (invalid) {
        return Promise.reject(new Error('Invalid post id'))
      }
      return bbsApi.getPost(postId)
    },
  )

  const deleteFn = useCallback((id: number) => bbsApi.deletePost(id), [])
  const { state: delState, mutate: deleteMut, reset: resetDelete } =
    useMutation(deleteFn)

  return (
    <div className="page">
      <h1>{invalid ? 'Post' : `Post #${postId}`}</h1>
      <p>
        <Link to="/">← Feed</Link>
      </p>

      <FetchStateDisplay state={state} onRetry={refetch}>
        {(post) => (
          <>
            <article className="post-card">
              <div className="post-card__meta">
                <Link to={`/users/${encodeURIComponent(post.username)}`}>{post.username}</Link>
                {' · '}
                <time dateTime={post.created_at}>{post.created_at}</time>
              </div>
              <p className="post-card__message">{post.message}</p>
            </article>

            <h2>Delete this post</h2>
            {delState.phase === 'loading' ? (
              <div className="inline-status inline-status--loading" role="status">
                <p>Deleting…</p>
              </div>
            ) : null}
            {delState.phase === 'error' ? (
              <div className="inline-status inline-status--error" role="alert">
                {delState.httpStatus === 422 ? (
                  <ServerValidationErrors body={delState.body} />
                ) : (
                  <p>{delState.message}</p>
                )}
              </div>
            ) : null}
            {delState.phase === 'success' ? <Navigate to="/" replace /> : null}
            {delState.phase === 'idle' || delState.phase === 'error' ? (
              <button
                type="button"
                className="btn btn-danger"
                onClick={() => {
                  resetDelete()
                  void deleteMut(post.id)
                }}
              >
                Delete permanently
              </button>
            ) : null}
          </>
        )}
      </FetchStateDisplay>
    </div>
  )
}
