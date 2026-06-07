import { useId, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useCurrentUser } from '../context/UserContext';
import { useCreateUser } from '../hooks/useCreateUser';
import { useConfirm } from '../context/ConfirmContext';
import { useToast } from '../context/ToastContext';
import { isUsernameSubmittable, validateUsername } from '../lib/validate';

export function LoginPage() {
  const { username, setUsername } = useCurrentUser();
  const navigate = useNavigate();
  const confirm = useConfirm();
  const { toast } = useToast();
  const createUser = useCreateUser();

  const [createName, setCreateName] = useState<string>('');
  const [switchName, setSwitchName] = useState<string>('');
  const createErrId = useId();
  const switchErrId = useId();

  const createServerErr = createUser.error?.fieldErrors?.username ?? createUser.error?.message;
  const createClientErr = createName ? validateUsername(createName) : null;
  const createErr = createServerErr ?? createClientErr;
  const createSubmittable = isUsernameSubmittable(createName) && !createUser.isPending;

  const switchClientErr = switchName ? validateUsername(switchName) : null;
  const switchSubmittable = isUsernameSubmittable(switchName);

  // If switching/signing-in changes who you are, the draft on the FeedPage
  // would silently belong to the new user. We don't have access to the draft
  // here (it's local state in PostForm), but we always confirm before
  // overriding an existing identity.
  async function trySetUser(next: string): Promise<boolean> {
    if (username && username !== next) {
      const ok = await confirm({
        title: `Switch from @${username} to @${next}?`,
        message: 'Any unsent draft on the feed page will be discarded.',
        confirmLabel: 'Switch',
      });
      if (!ok) return false;
    }
    setUsername(next);
    return true;
  }

  async function handleCreate(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    if (!createSubmittable) return;
    const result = await createUser.mutate(createName);
    if (result) {
      const ok = await trySetUser(createName);
      if (ok) {
        toast('success', `Welcome, @${createName}!`);
        navigate('/');
      }
    }
  }

  async function handleSwitch(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    if (!switchSubmittable) return;
    const ok = await trySetUser(switchName);
    if (ok) {
      toast('info', `Now posting as @${switchName}.`);
      navigate('/');
    }
  }

  function handleSignOut(): void {
    setUsername(null);
    toast('info', 'Signed out.');
  }

  return (
    <>
      <div className="page-header">
        <h1>{username ? 'Switch user' : 'Sign in'}</h1>
      </div>

      {username && (
        <div className="card" style={{ background: 'var(--bg-muted)' }}>
          <p style={{ margin: 0 }}>
            Currently signed in as <strong>@{username}</strong>.
          </p>
          <p style={{ margin: 'var(--space-2) 0 0', color: 'var(--fg-muted)', fontSize: 'var(--text-sm)' }}>
            X-Username is a preference, not a credential — switching just
            changes the header sent on your next post. <Link to={`/users/${username}`}>View profile</Link>.
          </p>
          <div style={{ marginTop: 'var(--space-3)' }}>
            <button type="button" className="btn btn--ghost btn--sm" onClick={handleSignOut}>
              Sign out
            </button>
          </div>
        </div>
      )}

      <form className="card" onSubmit={(e) => void handleCreate(e)}>
        <h2>Create a new account</h2>
        <div className="field" style={{ marginTop: 'var(--space-3)' }}>
          <label htmlFor="create-name" className="field__label">Username</label>
          <input
            id="create-name"
            type="text"
            value={createName}
            onChange={(e) => setCreateName(e.target.value)}
            placeholder="3–20 chars, letters/digits/underscore"
            aria-describedby={createErr ? createErrId : undefined}
            aria-invalid={!!createErr || undefined}
            autoComplete="off"
          />
          {createErr && (
            <div id={createErrId} className="field__error" role="alert">{createErr}</div>
          )}
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button type="submit" className="btn btn--primary" disabled={!createSubmittable}>
            {createUser.isPending ? 'Creating...' : 'Create account'}
          </button>
        </div>
      </form>

      <form className="card" onSubmit={(e) => void handleSwitch(e)}>
        <h2>Sign in as an existing user</h2>
        <div className="field" style={{ marginTop: 'var(--space-3)' }}>
          <label htmlFor="switch-name" className="field__label">Username</label>
          <input
            id="switch-name"
            type="text"
            value={switchName}
            onChange={(e) => setSwitchName(e.target.value)}
            placeholder="Existing username"
            aria-describedby={switchClientErr ? switchErrId : undefined}
            aria-invalid={!!switchClientErr || undefined}
            autoComplete="off"
          />
          {switchClientErr && (
            <div id={switchErrId} className="field__error" role="alert">{switchClientErr}</div>
          )}
          <div className="field__hint">
            No password — this just sets the X-Username header your posts send.
            See <Link to="/users">Users</Link> for the existing list.
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button type="submit" className="btn btn--ghost" disabled={!switchSubmittable}>
            Sign in
          </button>
        </div>
      </form>
    </>
  );
}
