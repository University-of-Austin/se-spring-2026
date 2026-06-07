import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { createUser, listUsers } from "../api/users";
import { useFetch } from "../hooks/useFetch";
import { useAuth } from "../auth/AuthContext";
import { Spinner } from "../components/Spinner";
import { ErrorBanner } from "../components/ErrorBanner";
import { useToast } from "../components/Toast";

const USERNAME_RE = /^[a-zA-Z0-9_]+$/;

export function SignUpPage() {
  const { username: current, setUsername } = useAuth();
  const { push } = useToast();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const fetcher = useCallback((signal: AbortSignal) => listUsers(signal), []);
  const { data: users, loading, error, refetch } = useFetch(fetcher, []);

  const trimmed = name.trim();
  const validLength = trimmed.length >= 3 && trimmed.length <= 20;
  const validShape = USERNAME_RE.test(trimmed);
  const canCreate = validLength && validShape && !busy;

  async function create() {
    if (!canCreate) return;
    setBusy(true);
    setErr(null);
    try {
      const u = await createUser(trimmed);
      setUsername(u.username);
      push(`Signed in as @${u.username}`, "info");
      navigate("/");
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Failed to create user");
    } finally {
      setBusy(false);
    }
  }

  function switchTo(u: string) {
    setUsername(u);
    push(`Switched to @${u}`, "info");
    navigate("/");
  }

  return (
    <div className="page signup-page">
      <h1>Sign in or create a user</h1>
      <p className="muted">
        Identity is just an <code>X-Username</code> header — pick any handle. No password,
        not real auth.
      </p>

      <section className="card">
        <h2>Create a new user</h2>
        <form
          className="signup-form"
          onSubmit={(e) => {
            e.preventDefault();
            create();
          }}
        >
          <label htmlFor="new-username">Username</label>
          <input
            id="new-username"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="3-20 chars: letters, digits, underscore"
            autoComplete="off"
            aria-invalid={trimmed.length > 0 && (!validLength || !validShape)}
            aria-describedby="username-hint username-err"
          />
          <p id="username-hint" className="hint">
            {trimmed.length === 0 && "3-20 chars, letters / digits / underscore only."}
            {trimmed.length > 0 && !validLength && "Must be 3-20 characters."}
            {trimmed.length > 0 && validLength && !validShape && "Only letters, digits, and underscore."}
            {validLength && validShape && "Looks good."}
          </p>
          <button type="submit" className="btn btn-primary" disabled={!canCreate}>
            {busy ? "Creating…" : "Create & sign in"}
          </button>
          {err && (
            <p id="username-err" className="compose-error" role="alert">
              {err}
            </p>
          )}
        </form>
      </section>

      <section className="card">
        <h2>Or switch to an existing user</h2>
        {current && <p className="muted">Currently signed in as @{current}.</p>}
        {loading && <Spinner />}
        {error && <ErrorBanner message={error} onRetry={refetch} />}
        {users && users.length === 0 && <p className="empty-state">No users yet.</p>}
        {users && users.length > 0 && (
          <ul className="switch-list">
            {users.map((u) => (
              <li key={u.username}>
                <button
                  type="button"
                  className="btn btn-ghost switch-row"
                  onClick={() => switchTo(u.username)}
                  disabled={current === u.username}
                >
                  <span>@{u.username}</span>
                  <span className="muted">
                    {u.post_count} post{u.post_count === 1 ? "" : "s"}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
