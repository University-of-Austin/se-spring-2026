import { useId, useState } from 'react';
import { Link } from 'react-router-dom';
import { POST_MAX, isPostSubmittable, validatePost } from '../lib/validate';
import { useCurrentUser } from '../context/UserContext';
import { useCreatePost } from '../hooks/useCreatePost';

type Props = {
  onPosted?: () => void;
};

// Compose form. Inline 422 errors via fieldErrors.message; live char count
// turns red past 500; submit disabled while pending OR while empty/over-limit.
// Cmd/Ctrl+Enter submits.
export function PostForm({ onPosted }: Props) {
  const { username } = useCurrentUser();
  const [text, setText] = useState<string>('');
  const { mutate, isPending, error, reset } = useCreatePost();

  const labelId = useId();
  const errorId = useId();

  const clientErr = validatePost(text);
  // 422 validation: error.fieldErrors.message is set, message-specific.
  // Any other error (404 user-not-found, 400 missing header, network):
  // fall back to the generic error.message so the user sees *something*.
  const fieldErr = error?.fieldErrors?.message ?? null;
  const generalErr = error && !fieldErr ? error.message : null;
  const errorMsg = fieldErr ?? generalErr ?? clientErr ?? null;
  const submittable = !!username && isPostSubmittable(text) && !isPending;

  async function submit(): Promise<void> {
    if (!submittable || !username) return;
    const result = await mutate({ message: text, username });
    if (result) {
      setText('');
      onPosted?.();
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>): void {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      void submit();
    }
  }

  if (!username) {
    return (
      <div className="card" style={{ background: 'var(--bg-muted)' }}>
        <p style={{ margin: 0, color: 'var(--fg-muted)' }}>
          <Link to="/login">Sign in or create an account</Link> to post.
        </p>
      </div>
    );
  }

  const overLimit = text.length > POST_MAX;

  return (
    <form
      className="card"
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      <div className="field">
        <label htmlFor={labelId} className="field__label">
          New post (as @{username})
        </label>
        <textarea
          id={labelId}
          data-shortcut="compose"
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            // Clear stale server error as soon as the user starts editing
            // again — they're acting on the feedback, no point keeping it.
            if (error) reset();
          }}
          onKeyDown={onKeyDown}
          placeholder="What's on your mind? (Cmd/Ctrl+Enter to post)"
          rows={3}
          aria-describedby={errorMsg ? errorId : undefined}
          aria-invalid={!!errorMsg || undefined}
        />
        <div
          className="field__hint"
          style={{ display: 'flex', justifyContent: 'space-between' }}
        >
          <span className={overLimit ? 'char-count char-count--over' : 'char-count'}>
            {text.length} / {POST_MAX}
          </span>
        </div>
        {errorMsg && (
          <div id={errorId} className="field__error" role="alert">
            {errorMsg}
          </div>
        )}
      </div>
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button
          type="submit"
          className="btn btn--primary"
          disabled={!submittable}
        >
          {isPending ? 'Posting...' : 'Post'}
        </button>
      </div>
    </form>
  );
}
