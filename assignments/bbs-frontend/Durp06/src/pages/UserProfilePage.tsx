import { useParams } from 'react-router-dom';
import { useUser } from '../hooks/useUser';
import { useUserPosts } from '../hooks/useUserPosts';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { PostCard } from '../components/PostCard';
import { useIdentity } from '../identity/IdentityContext';

export default function UserProfilePage() {
  const { username = '' } = useParams<{ username: string }>();
  const user = useUser(username);
  const posts = useUserPosts(username);
  const { username: me, setUsername } = useIdentity();

  if (user.loading) return <Loading label={`Loading @${username}`} />;
  if (user.error) {
    // Treat 404 as a dedicated view per spec.
    if (/not found/i.test(user.error)) {
      return (
        <section className="page page--user">
          <h1>@{username}</h1>
          <p className="empty">No such user.</p>
        </section>
      );
    }
    return <ErrorMessage message={user.error} onRetry={user.refetch} />;
  }
  if (!user.data) return null;

  const isMe = me === user.data.username;

  return (
    <section className="page page--user">
      <header className="page__head">
        <div>
          <h1>@{user.data.username}</h1>
          {user.data.bio && <p className="user__bio">{user.data.bio}</p>}
          <p className="user__meta">
            Joined <time dateTime={user.data.created_at}>{new Date(user.data.created_at).toLocaleDateString()}</time>
            {' · '}
            {user.data.post_count} post{user.data.post_count === 1 ? '' : 's'}
          </p>
        </div>
        {!isMe && (
          <button
            type="button"
            className="btn btn--primary btn--sm"
            onClick={() => setUsername(user.data!.username)}
          >
            Sign in as @{user.data.username}
          </button>
        )}
      </header>

      <h2 className="page__subhead">Posts</h2>
      {posts.loading && <Loading label="Loading posts" />}
      {posts.error && <ErrorMessage message={posts.error} onRetry={posts.refetch} />}
      {posts.data && posts.data.length === 0 && <p className="empty">No posts yet.</p>}
      {posts.data && posts.data.length > 0 && (
        <ul className="post-list" aria-label={`Posts by ${user.data.username}`}>
          {posts.data.map((p) => (
            <li key={p.id} className="post-list__item">
              <PostCard post={p} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
