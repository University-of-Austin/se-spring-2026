import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import { ApiError, type Post, type User } from "../types";
import { useAuth } from "../auth";
import { Avatar } from "../components/Avatar";
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
        <div className="profile-identity">
          {isSelf ? (
            <AvatarEditor user={user} onChange={setUser} />
          ) : (
            <Avatar username={user.username} src={user.avatar_url} size="xl" />
          )}
          <div className="profile-identity-text">
            <h1 className="profile-username">{user.username}</h1>
            <p className="profile-meta">
              Joined {new Date(user.created_at).toLocaleDateString()} · {user.post_count} posts
            </p>
          </div>
        </div>
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


function AvatarEditor({ user, onChange }: { user: User; onChange: (u: User) => void }) {
  const { token } = useAuth();
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function pick() { fileRef.current?.click(); }

  async function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";  // reset so picking the same file twice still fires
    if (!file || !token) return;

    if (file.size > 1_000_000) {
      setError("That image is over 1 MB. Try a smaller one.");
      return;
    }
    if (!/^image\/(png|jpeg|webp|gif)$/.test(file.type)) {
      setError("Use PNG, JPG, WebP, or GIF.");
      return;
    }

    setUploading(true);
    setError(null);
    try {
      const updated = await api.uploadAvatar(user.username, file, token);
      // Cache-bust so the new image shows even if the URL string didn't change.
      const busted = updated.avatar_url
        ? { ...updated, avatar_url: `${updated.avatar_url}?t=${Date.now()}` }
        : updated;
      onChange(busted);
      window.dispatchEvent(
        new CustomEvent("bbs:avatar-changed", { detail: { avatar_url: busted.avatar_url } }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not upload that image.");
    } finally {
      setUploading(false);
    }
  }

  async function onRemove() {
    if (!token) return;
    if (!confirm("Remove your profile picture?")) return;
    setUploading(true);
    setError(null);
    try {
      const updated = await api.deleteAvatar(user.username, token);
      onChange(updated);
      window.dispatchEvent(
        new CustomEvent("bbs:avatar-changed", { detail: { avatar_url: null } }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove avatar.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="avatar-editor">
      <Avatar username={user.username} src={user.avatar_url} size="xl" />
      <div className="avatar-editor-actions">
        <input
          ref={fileRef}
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif"
          onChange={onFileChange}
          className="visually-hidden"
          aria-label="Profile picture file"
        />
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={pick}
          disabled={uploading}
        >
          {uploading ? "Uploading..." : user.avatar_url ? "Change photo" : "Upload photo"}
        </button>
        {user.avatar_url && (
          <button
            type="button"
            className="btn btn-link btn-danger btn-sm"
            onClick={onRemove}
            disabled={uploading}
          >
            Remove
          </button>
        )}
      </div>
      {error && <div role="alert" className="inline-error avatar-editor-error">{error}</div>}
    </div>
  );
}
