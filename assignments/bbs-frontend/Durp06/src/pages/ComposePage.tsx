import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ApiError, createPost } from '../api/bbs';
import { useIdentity } from '../identity/IdentityContext';

const MAX_LEN = 500;

export default function ComposePage() {
  const { username } = useIdentity();
  const navigate = useNavigate();
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const trimmed = message.trim();
  const tooLong = message.length > MAX_LEN;
  const canSubmit = !!username && trimmed.length > 0 && !tooLong && !submitting;

  const submit = useCallback(async () => {
    if (!canSubmit || !username) return;
    setSubmitting(true);
    setError(null);
    try {
      await createPost(username, message);
      navigate('/');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : (err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }, [canSubmit, username, message, navigate]);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        void submit();
      }
    },
    [submit],
  );

  if (!username) {
    return (
      <section className="page page--compose">
        <h1>Compose</h1>
        <p className="empty">
          You need to be signed in to post. <Link to="/signup">Sign in or create an account.</Link>
        </p>
      </section>
    );
  }

  const counterClass = `compose__counter${tooLong ? ' compose__counter--over' : ''}`;

  return (
    <section className="page page--compose">
      <h1>New post</h1>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
        className="compose"
      >
        <label htmlFor="compose-message" className="compose__label">
          Message
        </label>
        <textarea
          id="compose-message"
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={onKeyDown}
          rows={6}
          placeholder="What's on your mind?"
          aria-describedby="compose-counter compose-help"
          aria-invalid={tooLong || undefined}
        />
        <div className="compose__bar">
          <span id="compose-counter" className={counterClass} aria-live="polite">
            {message.length} / {MAX_LEN}
          </span>
          <span id="compose-help" className="compose__hint">
            Press <kbd>Ctrl</kbd>/<kbd>⌘</kbd> + <kbd>Enter</kbd> to post.
          </span>
          <button type="submit" className="btn btn--primary" disabled={!canSubmit}>
            {submitting ? 'Posting…' : 'Post'}
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
