// Two-step username flow:
//   Step 1: user types a name and submits.
//   Step 2 (returning user): "Welcome back, alice. Is this you?" Yes/No confirm.
//   Step 2 (new user): silently create the user and continue.
//
// The "Is this you?" step makes the "X-Username isn't real auth" reality
// visible -- we literally can't verify identity, so we ask the user to
// confirm rather than pretending we know.

import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ErrorMessage } from "../../components/ErrorMessage";
import { useUsername } from "../../hooks/useUsername";
import { useCreateUser, useUserLookup } from "../../hooks/useUsers";
import { errorText } from "../../lib/errorText";
import styles from "./SignIn.module.css";

// Mirrors the A2 server-side rule: 3-20 chars, [a-zA-Z0-9_]+.
// Used to disable the submit button before the server says no.
const USERNAME_RE = /^[a-zA-Z0-9_]{3,20}$/;

type Step = "enter" | "confirm";

export function SignIn() {
  const navigate = useNavigate();
  const { setUsername } = useUsername();
  const lookupUser = useUserLookup();
  const createUser = useCreateUser();

  const [step, setStep] = useState<Step>("enter");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const valid = USERNAME_RE.test(name);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!valid || pending) return;
    setError(null);
    setPending(true);
    try {
      const existing = await lookupUser(name);
      if (existing) {
        setStep("confirm");
      } else {
        await createUser.mutateAsync(name);
        setUsername(name);
        navigate("/");
      }
    } catch (err) {
      setError(errorText(err, "Something went wrong. Try again."));
    } finally {
      setPending(false);
    }
  }

  function handleConfirmYes() {
    setUsername(name);
    navigate("/");
  }

  function handleConfirmNo() {
    setStep("enter");
    setName("");
    setError(null);
  }

  if (step === "confirm") {
    return (
      <section className={styles.card} aria-labelledby="confirm-heading">
        <h1 id="confirm-heading" className={styles.heading}>
          Welcome back, {name}.
        </h1>
        <p className={styles.subtitle}>Is this you?</p>
        <p className={styles.note}>
          Postack doesn't have real logins — anyone can claim to be anyone.
          Confirming just sets which name your posts will appear under.
        </p>
        <div className={styles.actions}>
          <button type="button" onClick={handleConfirmYes} className={styles.primary}>
            Yes, that's me
          </button>
          <button type="button" onClick={handleConfirmNo} className={styles.secondary}>
            No, not me
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className={styles.card} aria-labelledby="signin-heading">
      <h1 id="signin-heading" className={styles.heading}>Choose a username</h1>
      <p className={styles.subtitle}>
        Pick a name to use on Postack. New names create a new profile;
        existing names let you act as that user.
      </p>
      <form onSubmit={handleSubmit} className={styles.form}>
        <label htmlFor="username-input" className={styles.label}>
          Username
        </label>
        <input
          id="username-input"
          name="username"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. alice"
          autoComplete="off"
          autoFocus
          maxLength={20}
          aria-describedby="username-hint"
          className={styles.input}
        />
        <p id="username-hint" className={styles.hint}>
          3–20 characters. Letters, numbers, or underscores.
        </p>
        {error && <ErrorMessage message={error} />}
        <button type="submit" disabled={!valid || pending} className={styles.primary}>
          {pending ? "Checking..." : "Continue"}
        </button>
      </form>
    </section>
  );
}
