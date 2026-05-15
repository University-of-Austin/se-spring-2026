import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError, createUser } from '../api/bbs';
import { useIdentity } from '../identity/IdentityContext';

const USERNAME_RX = /^[a-zA-Z0-9_]+$/;
const MIN = 3;
const MAX = 20;

function validateUsername(input: string): string | null {
  if (input.length === 0) return null; // empty: not an error, just not submittable
  if (input.length < MIN) return `Username must be at least ${MIN} characters.`;
  if (input.length > MAX) return `Username must be at most ${MAX} characters.`;
  if (!USERNAME_RX.test(input)) return 'Only letters, numbers, and underscore allowed.';
  return null;
}

export default function SignupPage() {
  const { setUsername: setIdentity, username: current } = useIdentity();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [bio, setBio] = useState('');
  const [mode, setMode] = useState<'create' | 'switch'>('create');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clientError = validateUsername(username);
  const canSubmit = !!username && !clientError && !submitting;

  const submit = useCallback(async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      if (mode === 'create') {
        await createUser(username, bio);
      }
      setIdentity(username);
      navigate('/');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : (err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }, [canSubmit, mode, username, bio, setIdentity, navigate]);

  return (
    <section className="page page--signup">
      <h1>{mode === 'create' ? 'Create user' : 'Switch user'}</h1>
      {current && (
        <p className="signup__current">
          Currently signed in as <strong>@{current}</strong>.
        </p>
      )}
      <div className="tabs" role="tablist" aria-label="Auth mode">
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'create'}
          className={`tab${mode === 'create' ? ' tab--active' : ''}`}
          onClick={() => setMode('create')}
        >
          New account
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'switch'}
          className={`tab${mode === 'switch' ? ' tab--active' : ''}`}
          onClick={() => setMode('switch')}
        >
          Switch existing
        </button>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
        className="signup-form"
      >
        <label htmlFor="signup-username" className="signup-form__label">
          Username
        </label>
        <input
          id="signup-username"
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="off"
          autoCapitalize="off"
          spellCheck={false}
          aria-invalid={!!clientError || undefined}
          aria-describedby="signup-username-hint"
        />
        <span id="signup-username-hint" className="signup-form__hint">
          {clientError ?? `${MIN}–${MAX} letters, numbers, or underscore.`}
        </span>

        {mode === 'create' && (
          <>
            <label htmlFor="signup-bio" className="signup-form__label">
              Bio (optional)
            </label>
            <textarea
              id="signup-bio"
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              maxLength={200}
              rows={3}
            />
            <span className="signup-form__hint">{bio.length} / 200</span>
          </>
        )}

        <div className="signup-form__actions">
          <button type="submit" className="btn btn--primary" disabled={!canSubmit}>
            {submitting ? 'Working…' : mode === 'create' ? 'Create account' : 'Sign in'}
          </button>
        </div>
        {error && (
          <div className="error error--inline" role="alert">
            {error}
          </div>
        )}
      </form>
    </section>
  );
}
