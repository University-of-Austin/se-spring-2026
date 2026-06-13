import type { Post } from '../lib/types'
import { PostCard } from './PostCard'
import styles from './PostList.module.css'

interface PostListProps {
  posts: Post[]
  onDelete?: (post: Post) => void | Promise<void>
  onUpdated?: (post: Post) => void
}

export function PostList({ posts, onDelete, onUpdated }: PostListProps) {
  return (
    <div className={styles.list}>
      {posts.map((post) => (
        <PostCard
          key={post.id}
          post={post}
          onDelete={onDelete}
          onUpdated={onUpdated}
          // Optimistic posts use a temporary negative id until the server confirms.
          sending={post.id < 0}
        />
      ))}
    </div>
  )
}
