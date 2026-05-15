import { useCallback, useState } from "react";
import { useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { getUser, getUserPosts, patchUser } from "../api/users";
import { useFetch } from "../hooks/useFetch";
import { Spinner } from "../components/Spinner";
import { ErrorBanner } from "../components/ErrorBanner";
import { PostCard } from "../components/PostCard";
import { useAuth } from "../auth/AuthContext";
import { useToast } from "../components/Toast";

export function UserProfilePage() {
  const { username = "" } = useParams<{ username: string }>();
  const { username: me } = useAuth();
  const { push } = useToast();
  const userFetcher = useCallback((signal: AbortSignal) => getUser(username, signal), [username]);
  const postsFetcher = useCallback((signal: AbortSignal) => getUserPosts(username, signal), [username]);
  const user = useFetch(userFetcher, [username]);
  const posts = useFetch(postsFetcher, [username]);

  const [editing, setEditing] = useState(false);
  const [bioDraft, setBioDraft] = useState("");
  const [saving, setSaving] = useState(false);

  if (user.loading) return <Spinner label="Loading profile…" />;
  if (user.status === 404)
    return (
      <div className="page">
        <h1>User not found</h1>
        <p>No user named <code>@{username}</code> exists.</p>
      </div>
    );
  if (user.error || !user.data)
    return <ErrorBanner message={user.error ?? "Failed to load user"} onRetry={user.refetch} />;

  const u = user.data;
  const isMe = me === u.username;

  async function saveBio() {
    setSaving(true);
    try {
      const updated = await patchUser(u.username, bioDraft);
      user.setData(updated);
      setEditing(false);
      push("Bio updated", "info");
    } catch (err) {
      push(err instanceof ApiError ? err.message : "Failed to save bio", "error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page">
      <header className="profile-head">
        <h1>@{u.username}</h1>
        <p className="profile-meta">
          Joined {new Date(u.created_at + "Z").toLocaleDateString()} ·{" "}
          {u.post_count} post{u.post_count === 1 ? "" : "s"}
        </p>
        {!editing && (
          <div className="profile-bio-row">
            {u.bio ? <p className="profile-bio">{u.bio}</p> : <p className="profile-bio profile-bio-empty">No bio yet.</p>}
            {isMe && (
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => {
                  setBioDraft(u.bio);
                  setEditing(true);
                }}
              >
                Edit bio
              </button>
            )}
          </div>
        )}
        {editing && (
          <div className="profile-bio-editor">
            <label htmlFor="bio-edit" className="visually-hidden">Bio</label>
            <textarea
              id="bio-edit"
              value={bioDraft}
              onChange={(e) => setBioDraft(e.target.value)}
              maxLength={200}
              rows={3}
            />
            <div className="row">
              <span className="compose-count">{bioDraft.length}/200</span>
              <button type="button" className="btn btn-primary" onClick={saveBio} disabled={saving}>
                {saving ? "Saving…" : "Save"}
              </button>
              <button type="button" className="btn btn-ghost" onClick={() => setEditing(false)}>
                Cancel
              </button>
            </div>
          </div>
        )}
      </header>

      <h2>Posts</h2>
      {posts.loading && <Spinner />}
      {posts.error && <ErrorBanner message={posts.error} onRetry={posts.refetch} />}
      {posts.data && posts.data.length === 0 && (
        <p className="empty-state">@{u.username} hasn't posted yet.</p>
      )}
      {posts.data && (
        <ul className="post-list">
          {[...posts.data]
            .sort((a, b) => b.id - a.id)
            .map((p) => (
              <li key={p.id}>
                <PostCard post={p} />
              </li>
            ))}
        </ul>
      )}
    </div>
  );
}
