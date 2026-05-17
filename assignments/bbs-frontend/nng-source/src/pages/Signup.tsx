import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const USERNAME_RE = /^[a-zA-Z0-9_]+$/;

export function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const usernameValid =
    username.length >= 3 && username.length <= 20 && USERNAME_RE.test(username);
  const passwordValid = password.length >= 8;
  const canSubmit = !submitting && usernameValid && passwordValid;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      await signup(username, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign up.");
      setSubmitting(false);
    }
  }

  return (
    <div className="page page-auth">
      <h1>Create an account</h1>
      <form onSubmit={onSubmit} aria-label="Sign up" className="auth-form">
        <div className="form-row">
          <label htmlFor="signup-username">Username</label>
          <input
            id="signup-username"
            type="text"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            aria-invalid={username.length > 0 && !usernameValid}
            aria-describedby="signup-username-hint"
            required
          />
          <small id="signup-username-hint" className="hint">
            3–20 chars, letters/digits/underscore only.
          </small>
        </div>
        <div className="form-row">
          <label htmlFor="signup-password">Password</label>
          <input
            id="signup-password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-invalid={password.length > 0 && !passwordValid}
            aria-describedby="signup-password-hint"
            required
          />
          <small id="signup-password-hint" className="hint">
            At least 8 characters.
          </small>
        </div>
        {error && <div role="alert" className="inline-error">{error}</div>}
        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={!canSubmit}>
            {submitting ? "Creating..." : "Create account"}
          </button>
        </div>
      </form>
      <p className="auth-alt">
        Already have an account? <Link to="/login">Log in.</Link>
      </p>
    </div>
  );
}
