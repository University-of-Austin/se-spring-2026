import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import { ApiError, type Post, type User } from "../types";
import { useAuth } from "../auth";
import { ErrorBox } from "../components/ErrorBox";
import { PostCard } from "../components/PostCard";
import { Spinner } from "../components/Spinner";

const BIO_MAX = 200;

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
        <h1 className="profile-username">{user.username}</h1>
        <p className="profile-meta">
          Joined {new Date(user.created_at).toLocaleDateString()} · {user.post_count} posts
        </p>
        {isSelf ? <BioEditor user={user} onSaved={setUser} /> : (
          <p className="profile-bio">{user.bio || <em>(no bio set)</em>}</p>
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

function BioEditor({ user, onSaved }: { user: User; onSaved: (u: User) => void }) {
  const { token } = useAuth();
  const [bio, setBio] = useState(user.bio ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const tooLong = bio.length > BIO_MAX;
  const dirty = bio !== (user.bio ?? "");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token || saving || tooLong) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await api.patchBio(user.username, bio, token);
      onSaved(updated);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save bio.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="bio-editor" aria-label="Edit your bio">
      <label htmlFor="bio-input">Bio</label>
      <textarea
        id="bio-input"
        value={bio}
        onChange={(e) => { setBio(e.target.value); setSaved(false); }}
        rows={2}
        placeholder="A short bio..."
        aria-describedby="bio-count bio-error"
        aria-invalid={tooLong}
      />
      <div className="compose-footer">
        <span id="bio-count" className={tooLong ? "char-count char-count-over" : "char-count"}>
          {bio.length} / {BIO_MAX}
        </span>
        <button
          type="submit"
          className="btn btn-primary btn-sm"
          disabled={saving || tooLong || !dirty}
        >
          {saving ? "Saving..." : "Save bio"}
        </button>
      </div>
      {saved && <p className="inline-success" role="status">Bio saved.</p>}
      {error && <div id="bio-error" role="alert" className="inline-error">{error}</div>}
    </form>
  );
}
