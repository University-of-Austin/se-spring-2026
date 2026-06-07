import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { ApiError, type Post, type User } from "../types";
import { useAuth } from "../auth";
import { Avatar } from "../components/Avatar";
import { ErrorBox } from "../components/ErrorBox";
import { PostCard } from "../components/PostCard";
import { Spinner } from "../components/Spinner";

export function Profile() {
  const { username } = useParams<{ username: string }>();
  const me = useAuth();
  const target = username ?? "";

  const [user, setUser] = useState<User | null>(null);
  const [posts, setPosts] = useState<Post[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!target) return;
    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      const [u, ps] = await Promise.all([
        api.getUser(target),
        api.getUserPosts(target),
      ]);
      setUser(u);
      setPosts(ps);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setNotFound(true);
      } else {
        setError(err instanceof Error ? err.message : "Could not load profile.");
      }
    } finally {
      setLoading(false);
    }
  }, [target]);

  useEffect(() => { void load(); }, [load]);

  if (loading) return <div className="page"><Spinner label={`Loading ${target}...`} /></div>;
  if (notFound) {
    return (
      <div className="page page-notfound">
        <h1>User not found</h1>
        <p>No account exists with username <code>{target}</code>.</p>
      </div>
    );
  }
  if (error) return <div className="page"><ErrorBox message={error} onRetry={load} /></div>;
  if (!user) return null;

  const isSelf = me.username === user.username;

  async function onDelete(id: number) {
    if (!me.token) return;
    const snapshot = posts;
    setPosts((prev) => (prev ? prev.filter((p) => p.id !== id) : prev));
    try {
      await api.deletePost(id, me.token);
    } catch (err) {
      setPosts(snapshot);
      setError(err instanceof Error ? err.message : "Could not delete that post.");
    }
  }

  return (
    <div className="page page-profile">
      <header className="profile-header">
        <div className="profile-identity">
          <Avatar username={user.username} src={user.avatar_url} size="xl" />
          <div className="profile-identity-text">
            <h1 className="profile-username">{user.username}</h1>
            <p className="profile-meta">
              Joined {new Date(user.created_at).toLocaleDateString()} · {user.post_count} posts
            </p>
            {isSelf && (
              <p className="profile-self-actions">
                <Link to="/settings" className="btn btn-link btn-sm">Edit in Settings</Link>
              </p>
            )}
          </div>
        </div>
        <p className="profile-bio">{user.bio || <em>(no bio set)</em>}</p>
        {!isSelf && me.username && (
          <p className="profile-self-actions">
            <Link
              to={`/dms/${encodeURIComponent(user.username)}`}
              className="btn btn-secondary btn-sm"
            >
              Send a DM
            </Link>
          </p>
        )}
      </header>

      <section className="profile-posts">
        <h2>Posts by {user.username}</h2>
        {posts && posts.length === 0 && <p className="empty-state">No posts yet.</p>}
        {posts && posts.length > 0 && (
          <ul className="post-list" aria-label={`Posts by ${user.username}`}>
            {posts.map((p) => (
              <li key={p.id}>
                <PostCard post={p} showDelete={isSelf} onDelete={onDelete} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
