import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, api } from "../api/client";
import { ErrorBanner } from "../components/ErrorBanner";
import { Spinner } from "../components/Spinner";
import {
  USERNAME_MAX,
  USERNAME_MIN,
  USERNAME_REGEX,
} from "../api/types";
import { useApi } from "../hooks/useApi";
import { useUser } from "../hooks/useUser";

function validateUsername(name: string): string | null {
  if (name.length < USERNAME_MIN) return `At least ${USERNAME_MIN} characters.`;
  if (name.length > USERNAME_MAX) return `At most ${USERNAME_MAX} characters.`;
  if (!USERNAME_REGEX.test(name))
    return "Letters, numbers, and underscores only.";
  return null;
}

export function AuthPage() {
  const navigate = useNavigate();
  const { username: currentUser, setUsername, signOut } = useUser();
  const usersQuery = useApi((signal) => api.listUsers(signal), []);

  const [newUsername, setNewUsername] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [createError, setCreateError] = useState<ApiError | null>(null);

  const clientError = newUsername.length > 0 ? validateUsername(newUsername) : null;
  const canSubmit = !submitting && newUsername.length > 0 && !clientError;

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setCreateError(null);
    try {
      const user = await api.createUser(newUsername);
      setUsername(user.username);
      usersQuery.refetch();
      setNewUsername("");
      navigate(`/users/${encodeURIComponent(user.username)}`);
    } catch (err) {
      setCreateError(
        err instanceof ApiError ? err : new ApiError(0, String(err), err)
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>{currentUser ? "Switch user" : "Sign in"}</h1>
          <div className="sub">
            X-Username is a soft identity — anyone can sign in as anyone.
            That's the A2 contract.
          </div>
        </div>
      </div>

      {currentUser && (
        <div className="post" style={{ marginBottom: "var(--sp-4)" }}>
          <div className="field-label">Currently posting as</div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "var(--fs-20)" }}>
            {currentUser}
          </div>
          <div className="btn-row">
            <button type="button" className="btn btn-ghost" onClick={signOut}>
              Sign out
            </button>
          </div>
        </div>
      )}

      <form className="post" onSubmit={handleCreate} aria-label="Create new user">
        <div className="field">
          <label className="field-label" htmlFor="new-username">
            Create a new user
          </label>
          <input
            id="new-username"
            className="input"
            type="text"
            value={newUsername}
            onChange={(e) => setNewUsername(e.target.value)}
            placeholder="e.g. alice_42"
            aria-describedby="username-rules"
            aria-invalid={!!clientError}
            maxLength={USERNAME_MAX + 5}
            autoComplete="off"
          />
          <div className="field-foot">
            <span id="username-rules" className="field-hint">
              {USERNAME_MIN}–{USERNAME_MAX} chars, letters/numbers/underscore.
            </span>
            {clientError && (
              <span className="field-hint" style={{ color: "var(--danger)" }}>
                {clientError}
              </span>
            )}
          </div>
        </div>
        {createError && <ErrorBanner error={createError} />}
        <div className="btn-row" style={{ justifyContent: "flex-end" }}>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={!canSubmit}
          >
            {submitting ? (
              <>
                <span className="spinner" aria-hidden="true" /> Creating…
              </>
            ) : (
              "Create and sign in"
            )}
          </button>
        </div>
      </form>

      <div className="section-divider" />

      <h3 style={{ marginBottom: "var(--sp-3)" }}>Or pick an existing user</h3>
      {usersQuery.loading && !usersQuery.data && <Spinner label="Loading users" />}
      {usersQuery.error && (
        <ErrorBanner error={usersQuery.error} onRetry={usersQuery.refetch} />
      )}
      {usersQuery.data && usersQuery.data.length === 0 && (
        <p className="field-hint">No users yet — create one above.</p>
      )}
      {usersQuery.data && usersQuery.data.length > 0 && (
        <div className="user-list">
          {usersQuery.data.map((u) => (
            <button
              key={u.username}
              type="button"
              className="user-card"
              onClick={() => {
                setUsername(u.username);
                navigate("/");
              }}
              aria-label={`Sign in as ${u.username}`}
            >
              <span>{u.username}</span>
              <span className="count">
                {u.post_count} {u.post_count === 1 ? "post" : "posts"}
              </span>
            </button>
          ))}
        </div>
      )}
    </>
  );
}
