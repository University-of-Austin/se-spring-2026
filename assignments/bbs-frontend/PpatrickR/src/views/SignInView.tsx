import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { createUser, getUser } from "../api/users";
import { ApiError } from "../api/types";

const USERNAME_RE = /^[a-zA-Z0-9_]+$/;

export function SignInView({
  onSignedIn,
}: {
  onSignedIn: (username: string) => void;
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo =
    (location.state as { from?: string } | null)?.from ?? "/";

  const [mode, setMode] = useState<"switch" | "create">("create");
  const [username, setUsername] = useState("");
  const [bio, setBio] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const trimmed = username.trim();
  const lenOk = trimmed.length >= 3 && trimmed.length <= 20;
  const reOk = USERNAME_RE.test(trimmed);
  const valid = lenOk && reOk;

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!valid || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const user = await createUser(trimmed, bio.trim() || undefined);
      onSignedIn(user.username);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSwitch(e: React.FormEvent) {
    e.preventDefault();
    if (!valid || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await getUser(trimmed);
      onSignedIn(trimmed);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setError(
          `No user named @${trimmed} on the server. Switch to "Create user" to make one.`,
        );
      } else {
        setError(err instanceof ApiError ? err.detail : String(err));
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="view signin-view">
      <h1>Sign in</h1>
      <p className="muted">
        X-Username is not real auth — anything you type becomes your identity.
        Create a new user, or switch into one that already exists.
      </p>

      <div className="seg" role="tablist" aria-label="Sign-in mode">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "create"}
          className={"seg-btn" + (mode === "create" ? " active" : "")}
          onClick={() => setMode("create")}
        >
          Create user
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "switch"}
          className={"seg-btn" + (mode === "switch" ? " active" : "")}
          onClick={() => setMode("switch")}
        >
          Switch user
        </button>
      </div>

      <form onSubmit={mode === "create" ? handleCreate : handleSwitch}>
        <div className="field">
          <label htmlFor="username-input">Username</label>
          <input
            id="username-input"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="off"
            placeholder="alice"
            autoFocus
          />
          <div className="hint">
            3–20 chars, letters/digits/underscore.{" "}
            {trimmed && !reOk && (
              <span className="err">contains invalid characters</span>
            )}
            {trimmed && reOk && !lenOk && (
              <span className="err">must be 3–20 chars</span>
            )}
          </div>
        </div>

        {mode === "create" && (
          <div className="field">
            <label htmlFor="bio-input">Bio (optional)</label>
            <input
              id="bio-input"
              type="text"
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              maxLength={200}
              autoComplete="off"
            />
          </div>
        )}

        {error && (
          <div className="status error" role="alert">
            <div className="error-detail">{error}</div>
          </div>
        )}

        <button type="submit" className="primary" disabled={!valid || submitting}>
          {submitting
            ? "Working…"
            : mode === "create"
              ? "Create and sign in"
              : "Sign in as " + (trimmed || "…")}
        </button>
      </form>
    </section>
  );
}
