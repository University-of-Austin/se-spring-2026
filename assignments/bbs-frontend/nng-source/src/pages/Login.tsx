import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const USERNAME_RE = /^[a-zA-Z0-9_]+$/;

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const usernameValid =
    username.length >= 3 && username.length <= 20 && USERNAME_RE.test(username);
  const passwordValid = password.length >= 1;
  const canSubmit = !submitting && usernameValid && passwordValid;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      await login(username, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not log in.");
      setSubmitting(false);
    }
  }

  return (
    <div className="page page-auth">
      <h1>Log in</h1>
      <form onSubmit={onSubmit} aria-label="Log in" className="auth-form">
        <div className="form-row">
          <label htmlFor="login-username">Username</label>
          <input
            id="login-username"
            type="text"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            aria-invalid={username.length > 0 && !usernameValid}
            aria-describedby="login-username-hint"
            required
          />
          <small id="login-username-hint" className="hint">
            3–20 chars, letters/digits/underscore only.
          </small>
        </div>
        <div className="form-row">
          <label htmlFor="login-password">Password</label>
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        {error && <div role="alert" className="inline-error">{error}</div>}
        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={!canSubmit}>
            {submitting ? "Signing in..." : "Log in"}
          </button>
        </div>
      </form>
      <p className="auth-alt">
        New here? <Link to="/signup">Create an account.</Link>
      </p>
    </div>
  );
}
