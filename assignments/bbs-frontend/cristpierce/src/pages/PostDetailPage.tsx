import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, ApiError } from '../lib/api'
import type { Post } from '../lib/types'
import { usePost } from '../hooks/resources'
import { useToast } from '../context/ToastContext'
import { PostCard } from '../components/PostCard'
import { BackLink } from '../components/PageBits'
import { EmptyState, StateView } from '../components/ui/StateView'
import { PostCardSkeleton } from '../components/ui/Skeleton'
import styles from './PostDetailPage.module.css'

export function PostDetailPage() {
  const { id = '' } = useParams()
  const postId = Number(id)
  const navigate = useNavigate()
  const toast = useToast()
  const post = usePost(postId)

  async function handleDelete(p: Post) {
    try {
      await api.deletePost(p.id)
      toast.success('Post deleted.')
      navigate('/')
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Could not delete the post.')
    }
  }

  function handleUpdated(updated: Post) {
    post.setData(updated)
  }

  if (!Number.isFinite(postId) || postId <= 0) {
    return (
      <div className={styles.page}>
        <BackLink to="/">Back to feed</BackLink>
        <EmptyState title="Invalid post link" hint={<Link to="/">Go to the feed →</Link>} />
      </div>
    )
  }

  if (post.isError && post.error?.status === 404) {
    return (
      <div className={styles.page}>
        <BackLink to="/">Back to feed</BackLink>
        <EmptyState
          title="Post not found"
          hint={<Link to="/">It may have been deleted. Back to the feed →</Link>}
        />
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <BackLink to="/">Back to feed</BackLink>
      <StateView
        status={post.status}
        data={post.data}
        error={post.error}
        onRetry={post.refetch}
        errorTitle="Couldn’t load this post"
        loading={<PostCardSkeleton />}
      >
        {(p) => <PostCard post={p} onDelete={handleDelete} onUpdated={handleUpdated} />}
      </StateView>
    </div>
  )
}
