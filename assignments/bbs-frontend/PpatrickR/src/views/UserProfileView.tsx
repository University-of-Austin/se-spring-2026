import { useCallback } from "react";
import { Link } from "react-router-dom";
import { getUser, listUserPosts } from "../api/users";
import { useFetch } from "../hooks/useFetch";
import { Loading, ErrorBlock } from "../components/StatusBlock";
import { PostRow } from "../components/PostRow";

export function UserProfileView({ username }: { username: string }) {
  const userFetcher = useCallback(() => getUser(username), [username]);
  const postsFetcher = useCallback(() => listUserPosts(username), [username]);

  const userQ = useFetch(userFetcher, [username]);
  const postsQ = useFetch(postsFetcher, [username]);

  if (userQ.loading) {
    return (
      <section className="view profile-view">
        <Loading label={`Loading @${username}…`} />
      </section>
    );
  }

  if (userQ.error) {
    if (userQ.error.status === 404) {
      return (
        <section className="view profile-view">
          <h1>User not found</h1>
          <p className="muted">
            No user named <strong>@{username}</strong>.
          </p>
          <Link to="/users" className="secondary">
            ← Back to users
          </Link>
        </section>
      );
    }
    return (
      <section className="view profile-view">
        <ErrorBlock error={userQ.error} onRetry={userQ.reload} />
      </section>
    );
  }

  const user = userQ.data;
  if (!user) return null;

  return (
    <section className="view profile-view">
      <h1>@{user.username}</h1>
      <div className="muted small">
        Joined {new Date(user.created_at).toLocaleDateString()} ·{" "}
        {user.post_count} post{user.post_count === 1 ? "" : "s"}
      </div>
      {user.bio && <p className="bio">{user.bio}</p>}

      <h2>Posts</h2>
      {postsQ.loading && <Loading />}
      {postsQ.error && (
        <ErrorBlock error={postsQ.error} onRetry={postsQ.reload} />
      )}
      {!postsQ.loading &&
        !postsQ.error &&
        postsQ.data &&
        (postsQ.data.length === 0 ? (
          <div className="empty">@{user.username} hasn't posted yet.</div>
        ) : (
          <div className="post-list">
            {postsQ.data.map((p) => (
              <PostRow key={p.id} post={p} showAuthor={false} />
            ))}
          </div>
        ))}
    </section>
  );
}
