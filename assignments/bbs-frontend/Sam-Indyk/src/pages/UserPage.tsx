import { Link, useParams } from "react-router-dom";
import { ApiError, api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { PostRow } from "../components/PostRow";
import { Spinner } from "../components/Spinner";
import { useApi } from "../hooks/useApi";
import { useUser } from "../hooks/useUser";

export function UserPage() {
  const { username = "" } = useParams<{ username: string }>();
  const { username: currentUser, setUsername } = useUser();

  const userQuery = useApi((signal) => api.getUser(username, signal), [username]);
  const postsQuery = useApi(
    (signal) => api.getUserPosts(username, signal),
    [username]
  );

  if (userQuery.loading && !userQuery.data) return <Spinner label="Loading user" />;

  if (userQuery.error) {
    const isNotFound =
      userQuery.error instanceof ApiError && userQuery.error.status === 404;
    if (isNotFound) {
      return (
        <EmptyState
          title={`User "${username}" not found`}
          description="Maybe they haven't signed up yet."
          action={
            <Link to="/users" className="btn">
              Back to users
            </Link>
          }
        />
      );
    }
    return <ErrorBanner error={userQuery.error} onRetry={userQuery.refetch} />;
  }

  const user = userQuery.data;
  if (!user) return null;

  const isSelf = currentUser === user.username;

  return (
    <>
      <div className="profile-head">
        <div className="username">{user.username}</div>
        <div className="meta">
          Joined {new Date(user.created_at).toLocaleDateString()} ·{" "}
          {user.post_count} {user.post_count === 1 ? "post" : "posts"}
        </div>
        {user.bio && <div className="bio">{user.bio}</div>}
        <div className="btn-row" style={{ marginTop: "var(--sp-2)" }}>
          {!isSelf && (
            <button
              type="button"
              className="btn"
              onClick={() => setUsername(user.username)}
            >
              Sign in as {user.username}
            </button>
          )}
          {isSelf && (
            <span className="field-hint">This is you.</span>
          )}
        </div>
      </div>

      <h3 style={{ marginBottom: "var(--sp-3)" }}>Posts</h3>

      {postsQuery.loading && !postsQuery.data && <Spinner label="Loading posts" />}
      {postsQuery.error && (
        <ErrorBanner error={postsQuery.error} onRetry={postsQuery.refetch} />
      )}
      {postsQuery.data && postsQuery.data.length === 0 && (
        <EmptyState
          title="No posts yet"
          description={`${user.username} hasn't posted anything.`}
        />
      )}
      {postsQuery.data && postsQuery.data.length > 0 && (
        <div className="post-list">
          {postsQuery.data.map((p) => (
            <PostRow key={p.id} post={p} />
          ))}
        </div>
      )}
    </>
  );
}
