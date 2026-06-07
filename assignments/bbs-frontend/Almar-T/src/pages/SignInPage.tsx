import { useId, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { createUser, getUser } from "../api/users";
import { ApiError } from "../api/types";
import { useCurrentUser } from "../hooks/useCurrentUser";
import { useToast } from "../hooks/useToast";
import styles from "./SignInPage.module.css";

const USERNAME_RE = /^[a-zA-Z0-9_]+$/;

function validateUsername(u: string): string | null {
  if (u.length < 3) return "Username must be at least 3 characters.";
  if (u.length > 20) return "Username must be at most 20 characters.";
  if (!USERNAME_RE.test(u)) return "Letters, numbers, and underscores only.";
  return null;
}

export default function SignInPage() {
  const navigate = useNavigate();
  const { currentUser, setCurrentUser } = useCurrentUser();
  const { show } = useToast();

  const [switchValue, setSwitchValue] = useState("");
  const [switchError, setSwitchError] = useState<string | null>(null);
  const [switchBusy, setSwitchBusy] = useState(false);

  const [createValue, setCreateValue] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [createBusy, setCreateBusy] = useState(false);

  const switchId = useId();
  const createId = useId();

  const onSwitch = async (e: FormEvent) => {
    e.preventDefault();
    const u = switchValue.trim();
    const v = validateUsername(u);
    if (v) {
      setSwitchError(v);
      return;
    }
    setSwitchBusy(true);
    setSwitchError(null);
    try {
      // Verify the user exists before storing — silent failure is worse
      // than a clear "no such user" message here.
      await getUser(u);
      setCurrentUser(u);
      show(`Signed in as @${u}`, "success");
      navigate("/");
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        setSwitchError(`No user named @${u}. Create one below?`);
      } else {
        setSwitchError(e instanceof ApiError ? e.detail : String(e));
      }
    } finally {
      setSwitchBusy(false);
    }
  };

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    const u = createValue.trim();
    const v = validateUsername(u);
    if (v) {
      setCreateError(v);
      return;
    }
    setCreateBusy(true);
    setCreateError(null);
    try {
      await createUser(u);
      setCurrentUser(u);
      show(`Created and signed in as @${u}`, "success");
      navigate("/");
    } catch (e) {
      setCreateError(e instanceof ApiError ? e.detail : String(e));
    } finally {
      setCreateBusy(false);
    }
  };

  const switchValidationError =
    switchValue && !switchError ? validateUsername(switchValue.trim()) : null;
  const createValidationError =
    createValue && !createError ? validateUsername(createValue.trim()) : null;

  return (
    <div className={styles.page}>
      <header>
        <h1>Sign in</h1>
        <p className="muted">
          BBS uses your username as your identity. This is{" "}
          <strong>not real authentication</strong> — it's a preference saved in
          your browser's localStorage, sent with each post in the{" "}
          <code>X-Username</code> header. Anyone can claim any name.
        </p>
        {currentUser && (
          <p className={styles.currentNote}>
            You're currently signed in as <strong>@{currentUser}</strong>.
          </p>
        )}
      </header>

      <section className={styles.section}>
        <h2>Switch user</h2>
        <form onSubmit={onSwitch} className={styles.form}>
          <label htmlFor={switchId} className="label">
            Existing username
          </label>
          <input
            id={switchId}
            className="input"
            value={switchValue}
            onChange={(e) => {
              setSwitchValue(e.target.value);
              setSwitchError(null);
            }}
            placeholder="alice"
            autoComplete="off"
            aria-invalid={!!switchError || !!switchValidationError}
            aria-describedby={
              switchError || switchValidationError
                ? `${switchId}-err`
                : undefined
            }
          />
          {(switchError || switchValidationError) && (
            <p
              id={`${switchId}-err`}
              className="error-text"
              role={switchError ? "alert" : undefined}
            >
              {switchError ?? switchValidationError}
            </p>
          )}
          <button
            type="submit"
            className="btn btn-primary"
            disabled={
              switchBusy || !switchValue.trim() || !!switchValidationError
            }
          >
            {switchBusy ? "Checking…" : "Sign in"}
          </button>
        </form>
      </section>

      <section className={styles.section}>
        <h2>Create new user</h2>
        <form onSubmit={onCreate} className={styles.form}>
          <label htmlFor={createId} className="label">
            New username (3–20 chars, letters/numbers/underscores)
          </label>
          <input
            id={createId}
            className="input"
            value={createValue}
            onChange={(e) => {
              setCreateValue(e.target.value);
              setCreateError(null);
            }}
            placeholder="new_user"
            autoComplete="off"
            aria-invalid={!!createError || !!createValidationError}
            aria-describedby={
              createError || createValidationError
                ? `${createId}-err`
                : undefined
            }
          />
          {(createError || createValidationError) && (
            <p
              id={`${createId}-err`}
              className="error-text"
              role={createError ? "alert" : undefined}
            >
              {createError ?? createValidationError}
            </p>
          )}
          <button
            type="submit"
            className="btn"
            disabled={
              createBusy || !createValue.trim() || !!createValidationError
            }
          >
            {createBusy ? "Creating…" : "Create + sign in"}
          </button>
        </form>
      </section>
    </div>
  );
}
