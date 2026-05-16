import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { Avatar } from "../components/Avatar";
import { ErrorBox } from "../components/ErrorBox";
import { Spinner } from "../components/Spinner";
import type { User } from "../types";

const BIO_MAX = 200;
const PW_MIN = 8;

export function Settings() {
  const { username, token, logout } = useAuth();
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!username) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    try {
      setUser(await api.getUser(username));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load your profile.");
    } finally {
      setLoading(false);
    }
  }, [username]);

  useEffect(() => { void load(); }, [load]);

  if (!username || !token) {
    return (
      <div className="page page-settings">
        <h1>Settings</h1>
        <p className="empty-state">Log in to manage your account.</p>
      </div>
    );
  }

  if (loading) return <div className="page"><Spinner label="Loading your settings..." /></div>;
  if (error) return <div className="page"><ErrorBox message={error} onRetry={load} /></div>;
  if (!user) return null;

  return (
    <div className="page page-settings">
      <h1>Settings</h1>

      <section className="settings-section" aria-labelledby="settings-avatar-heading">
        <h2 id="settings-avatar-heading">Profile picture</h2>
        <AvatarEditor user={user} onChange={setUser} />
      </section>

      <section className="settings-section" aria-labelledby="settings-bio-heading">
        <h2 id="settings-bio-heading">Bio</h2>
        <BioEditor user={user} onSaved={setUser} />
      </section>

      <section className="settings-section" aria-labelledby="settings-pw-heading">
        <h2 id="settings-pw-heading">Change password</h2>
        <PasswordEditor onChanged={() => {
          // On success, force the user to sign in again.
          void logout().then(() => navigate("/login"));
        }} />
      </section>

      <p className="auth-alt">
        Want to see your public profile?{" "}
        <Link to={`/users/${encodeURIComponent(username)}`}>View profile</Link>
      </p>
    </div>
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
    e.target.value = "";
    if (!file || !token) return;

    if (file.size > 1_000_000) { setError("Image is over 1 MB."); return; }
    if (!/^image\/(png|jpeg|webp|gif)$/.test(file.type)) {
      setError("Use PNG, JPG, WebP, or GIF."); return;
    }

    setUploading(true);
    setError(null);
    try {
      const updated = await api.uploadAvatar(user.username, file, token);
      const busted = updated.avatar_url
        ? { ...updated, avatar_url: `${updated.avatar_url}?t=${Date.now()}` }
        : updated;
      onChange(busted);
      window.dispatchEvent(
        new CustomEvent("bbs:avatar-changed", { detail: { avatar_url: busted.avatar_url } }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not upload image.");
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
    <div className="avatar-editor avatar-editor-horiz">
      <Avatar username={user.username} src={user.avatar_url} size="lg" />
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
        {error && <div role="alert" className="inline-error avatar-editor-error">{error}</div>}
      </div>
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
      <label htmlFor="bio-input" className="visually-hidden">Bio</label>
      <textarea
        id="bio-input"
        value={bio}
        onChange={(e) => { setBio(e.target.value); setSaved(false); }}
        rows={3}
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


function PasswordEditor({ onChanged }: { onChanged: () => void }) {
  const { username, token } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const nextTooShort = next.length > 0 && next.length < PW_MIN;
  const mismatch = confirm.length > 0 && confirm !== next;
  const canSubmit =
    !saving && current.length > 0 && next.length >= PW_MIN && confirm === next;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit || !username || !token) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await api.changePassword(username, current, next, token);
      setSaved(true);
      setCurrent(""); setNext(""); setConfirm("");
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not change password.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="password-editor" aria-label="Change your password">
      <div className="form-row">
        <label htmlFor="pw-current">Current password</label>
        <input
          id="pw-current"
          type="password"
          autoComplete="current-password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          required
        />
      </div>
      <div className="form-row">
        <label htmlFor="pw-next">New password</label>
        <input
          id="pw-next"
          type="password"
          autoComplete="new-password"
          value={next}
          onChange={(e) => setNext(e.target.value)}
          aria-invalid={nextTooShort}
          aria-describedby="pw-next-hint"
          required
        />
        <small id="pw-next-hint" className="hint">At least {PW_MIN} characters.</small>
      </div>
      <div className="form-row">
        <label htmlFor="pw-confirm">Confirm new password</label>
        <input
          id="pw-confirm"
          type="password"
          autoComplete="new-password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          aria-invalid={mismatch}
          required
        />
        {mismatch && <small className="hint" style={{ color: "var(--danger)" }}>Doesn't match.</small>}
      </div>
      <div className="form-actions">
        <button type="submit" className="btn btn-primary btn-sm" disabled={!canSubmit}>
          {saving ? "Updating..." : "Update password"}
        </button>
      </div>
      {saved && (
        <p className="inline-success" role="status">
          Password updated. Signing you out so you can log back in.
        </p>
      )}
      {error && <div role="alert" className="inline-error">{error}</div>}
    </form>
  );
}
