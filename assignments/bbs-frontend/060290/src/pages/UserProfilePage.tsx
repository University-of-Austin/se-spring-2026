import { useParams, Link } from 'react-router-dom'
import { useMountFetch } from '../hooks/useMountFetch'
import { bbsApi } from '../api/bbs'
import { FetchStateDisplay } from '../components/FetchStateDisplay'
import { PostCard } from '../components/PostCard'
import './pages.css'

export function UserProfilePage() {
  const { username: usernameParam } = useParams<{ username: string }>()
  const username = decodeURIComponent(usernameParam ?? '')

  const userFetch = useMountFetch(`user-profile:${username}`, () =>
    bbsApi.getUser(username),
  )
  const postsFetch = useMountFetch(`user-posts:${username}`, () =>
    bbsApi.getUserPosts(username),
  )

  return (
    <div className="page">
      <h1>User: {username}</h1>
      <p>
        <Link to="/users">← All users</Link>
      </p>

      <h2>Profile</h2>
      <FetchStateDisplay state={userFetch.state} onRetry={userFetch.refetch}>
        {(user) => (
          <dl>
            <dt>Username</dt>
            <dd>{user.username}</dd>
            <dt>Created</dt>
            <dd>
              <time dateTime={user.created_at}>{user.created_at}</time>
            </dd>
          </dl>
        )}
      </FetchStateDisplay>

      <h2>Posts</h2>
      <FetchStateDisplay state={postsFetch.state} onRetry={postsFetch.refetch}>
        {(posts) =>
          posts.length === 0 ? (
            <p className="empty-hint">This user has not posted yet.</p>
          ) : (
            <ul className="post-list">
              {posts.map((p) => (
                <PostCard key={p.id} post={p} />
              ))}
            </ul>
          )
        }
      </FetchStateDisplay>
    </div>
  )
}
