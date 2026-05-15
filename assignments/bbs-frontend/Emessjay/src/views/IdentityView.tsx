// Sign up + switch user, plus a "currently posting as" banner.
//
// Two forms in one page:
//   1) Create a new user.  Validates the username against A2's regex
//      and length bounds on every keystroke; submit disabled when
//      invalid.  On 409 (duplicate), shows inline "username taken".
//   2) Switch to an existing user.  Populated from GET /users.
//
// Sign-out clears localStorage via useCurrentUser().setUsername(null).
// We don't talk to the server for sign-in/sign-out — X-Username is
// just a header we attach to the next POST.

import { useState } from "react";
import { useCurrentUser } from "../hooks/useCurrentUser";
import { useUsers } from "../hooks/useUsers";
import { useRouter } from "../router/useRouter";
import { createUser } from "../api/endpoints";
import { ApiError } from "../api/client";
import { Loadable } from "../components/Loadable";
import { ApiErrorMessage } from "../components/ApiErrorMessage";
import styles from "./IdentityView.module.css";

const USERNAME_RE = /^[a-zA-Z0-9_]+$/;
const MIN_LEN = 3;
const MAX_LEN = 20;

function usernameValidity(name: string): { ok: boolean; reason: string | null } {
  if (name.length === 0) return { ok: false, reason: null };
  if (name.length < MIN_LEN) return { ok: false, reason: `At least ${MIN_LEN} characters.` };
  if (name.length > MAX_LEN) return { ok: false, reason: `At most ${MAX_LEN} characters.` };
  if (!USERNAME_RE.test(name)) return { ok: false, reason: "Letters, digits, and underscores only." };
  return { ok: true, reason: null };
}

export function IdentityView() {
  const { username, setUsername } = useCurrentUser();
  const { navigate } = useRouter();

  // Sign-up form state
  const [newName, setNewName] = useState("");
  const [signupError, setSignupError] = useState<ApiError | null>(null);
  const [signupBusy, setSignupBusy] = useState(false);
  const validity = usernameValidity(newName);

  // Switch-user form state
  const usersState = useUsers();
  const [pickedUser, setPickedUser] = useState("");

  async function onSignUp() {
    if (!validity.ok || signupBusy) return;
    setSignupBusy(true);
    setSignupError(null);
    try {
      const u = await createUser(newName);
      setUsername(u.username);
      setNewName("");
      navigate({ view: "feed" });
    } catch (err) {
      setSignupError(err instanceof ApiError ? err : new ApiError(0, "Sign up failed"));
    } finally {
      setSignupBusy(false);
    }
  }

  function onSwitch() {
    if (pickedUser) {
      setUsername(pickedUser);
      navigate({ view: "feed" });
    }
  }

  return (
    <div className={styles.wrap}>
      <h2 className={styles.title}>Identity</h2>

      <section className={styles.section} aria-labelledby="current-heading">
        <h3 id="current-heading" className={styles.sectionTitle}>Current</h3>
        {username ? (
          <p className={styles.current}>
            Posting as <strong>@{username}</strong>{" "}
            <button
              type="button"
              className={styles.signOut}
              onClick={() => setUsername(null)}
            >
              Sign out
            </button>
          </p>
        ) : (
          <p className={styles.current}>Not signed in.</p>
        )}
      </section>

      <section className={styles.section} aria-labelledby="signup-heading">
        <h3 id="signup-heading" className={styles.sectionTitle}>Create a new user</h3>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSignUp();
          }}
        >
          <label htmlFor="signup-name" className={styles.label}>Username</label>
          <input
            id="signup-name"
            type="text"
            className={styles.input}
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="alice_42"
            autoComplete="off"
            spellCheck={false}
            aria-invalid={!validity.ok && newName.length > 0}
            aria-describedby="signup-hint"
          />
          <p id="signup-hint" className={styles.hint}>
            {validity.reason ?? "3–20 characters; letters, digits, underscores."}
          </p>
          <button
            type="submit"
            className={styles.primary}
            disabled={!validity.ok || signupBusy}
          >
            {signupBusy ? "Creating…" : "Create user"}
          </button>
          {signupError && <ApiErrorMessage error={signupError} />}
        </form>
      </section>

      <section className={styles.section} aria-labelledby="switch-heading">
        <h3 id="switch-heading" className={styles.sectionTitle}>Switch user</h3>
        <Loadable state={usersState} emptyMessage="No users to switch to yet.">
          {(users) => (
            <div className={styles.switchRow}>
              <label htmlFor="switch-pick" className={styles.label}>Pick an existing user</label>
              <select
                id="switch-pick"
                className={styles.input}
                value={pickedUser}
                onChange={(e) => setPickedUser(e.target.value)}
              >
                <option value="">— select —</option>
                {users.map((u) => (
                  <option key={u.username} value={u.username}>@{u.username}</option>
                ))}
              </select>
              <button
                type="button"
                className={styles.primary}
                onClick={onSwitch}
                disabled={!pickedUser}
              >
                Use this name
              </button>
            </div>
          )}
        </Loadable>
      </section>
    </div>
  );
}
