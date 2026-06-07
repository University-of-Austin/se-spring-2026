import { useCallback, useId, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ErrorBlock, LoadingBlock } from "../components/StatusBlock";
import { useApi } from "../hooks/useApi";
import { useCurrentUser } from "../hooks/useCurrentUser";
import { ApiError, api } from "../lib/api";
import { setStoredUsername } from "../lib/storage";
import styles from "./SignupView.module.css";

const USERNAME_RE = /^[a-zA-Z0-9_]+$/;
const SUGGESTION_LIMIT = 8;

export function SignupView() {
  const navigate = useNavigate();
  const me = useCurrentUser();

  const fetcher = useCallback((signal: AbortSignal) => api.listUsers(signal), []);
  const users = useApi(fetcher, "users");

  const [newName, setNewName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const createId = useId();

  const validNew = newName.length >= 3 && newName.length <= 20 && USERNAME_RE.test(newName);

  const create = async () => {
    if (!validNew) return;
    setCreating(true);
    setError(null);
    try {
      const u = await api.createUser(newName);
      setStoredUsername(u.username);
      navigate("/");
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : (e as Error).message ?? "create failed",
      );
    } finally {
      setCreating(false);
    }
  };

  return (
    <section className={styles.wrap}>
      <div className={styles.card}>
        <h1 className={styles.title}>create a user</h1>
        <p className={styles.description}>
          your "identity" is just an <code>X-Username</code> header. anyone can
          pick any name. picking yours stores it locally so refreshes keep you
          signed in.
        </p>
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault();
            void create();
          }}
        >
          <label htmlFor={createId} className="sr-only">
            New username
          </label>
          <div className={styles.row}>
            <input
              id={createId}
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="3-20 chars, letters/numbers/_"
              maxLength={20}
              autoComplete="off"
              aria-invalid={newName.length > 0 && !validNew}
            />
            <button
              type="submit"
              className={styles.btnPrimary}
              disabled={!validNew || creating}
            >
              {creating ? "creating…" : "create + sign in"}
            </button>
          </div>
          <span className={styles.hint}>
            usernames must match <code>^[a-zA-Z0-9_]+$</code>, length 3-20.
          </span>
          {error && <div className={styles.error} role="alert">{error}</div>}
        </form>
      </div>

      <div className={styles.card}>
        <h2 className={styles.title}>sign in as an existing user</h2>
        <p className={styles.description}>
          start typing your username. suggestions appear below as you type.
        </p>
        <SignInCombobox
          users={users.data ?? null}
          loading={users.loading}
          error={users.error}
          onRetry={users.refetch}
          currentUsername={me}
          onPick={(name) => {
            setStoredUsername(name);
            navigate(`/users/${name}`);
          }}
        />
      </div>
    </section>
  );
}

type ComboboxProps = {
  users: { username: string }[] | null;
  loading: boolean;
  error: Error | null;
  onRetry: () => void;
  currentUsername: string | null;
  onPick: (username: string) => void;
};

// ARIA combobox over the username list. Open while focused; arrow keys move
// the active option; Enter picks; Escape closes. Submitting a name that isn't
// in the user list surfaces an inline error instead of silently setting
// localStorage to a name that future POSTs will 404 on.
function SignInCombobox({
  users,
  loading,
  error,
  onRetry,
  currentUsername,
  onPick,
}: ComboboxProps) {
  const inputId = useId();
  const listId = useId();
  const inputRef = useRef<HTMLInputElement>(null);

  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const [pickError, setPickError] = useState<string | null>(null);

  const suggestions = useMemo(() => {
    if (!users) return [];
    const q = query.trim().toLowerCase();
    const matches = q
      ? users.filter((u) => u.username.toLowerCase().includes(q))
      : users;
    return matches.slice(0, SUGGESTION_LIMIT);
  }, [users, query]);

  const submitWith = (name: string) => {
    const exists = users?.some((u) => u.username === name);
    if (!exists) {
      setPickError(`no user named @${name}. create one above?`);
      return;
    }
    setPickError(null);
    onPick(name);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setHighlight((h) =>
        suggestions.length === 0 ? 0 : Math.min(suggestions.length - 1, h + 1),
      );
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((h) => Math.max(0, h - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (open && suggestions.length > 0) {
        submitWith(suggestions[highlight].username);
      } else if (query.trim()) {
        submitWith(query.trim());
      }
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  // mousedown rather than click because the input's blur fires first on click
  // and the dropdown would unmount before the click handler runs. preventDefault
  // also keeps focus on the input through the interaction.
  const onOptionMouseDown = (e: React.MouseEvent, username: string) => {
    e.preventDefault();
    submitWith(username);
  };

  const showDropdown = open && suggestions.length > 0;
  const activeId = showDropdown ? `${listId}-opt-${highlight}` : undefined;

  return (
    <div className={styles.form}>
      <label htmlFor={inputId} className="sr-only">
        Username
      </label>
      <div className={styles.row}>
        <div className={styles.combobox}>
          <input
            id={inputId}
            ref={inputRef}
            type="text"
            role="combobox"
            aria-expanded={showDropdown}
            aria-controls={listId}
            aria-autocomplete="list"
            aria-activedescendant={activeId}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setHighlight(0);
              setOpen(true);
              setPickError(null);
            }}
            onFocus={() => setOpen(true)}
            onBlur={() => setOpen(false)}
            onKeyDown={onKeyDown}
            placeholder="start typing a username"
            maxLength={20}
            autoComplete="off"
            disabled={loading || !!error}
          />
          {showDropdown && (
            <ul
              id={listId}
              role="listbox"
              aria-label="Matching usernames"
              className={styles.listbox}
            >
              {suggestions.map((u, i) => (
                <li
                  key={u.username}
                  id={`${listId}-opt-${i}`}
                  role="option"
                  aria-selected={i === highlight}
                  className={
                    i === highlight ? styles.optionActive : styles.option
                  }
                  onMouseDown={(e) => onOptionMouseDown(e, u.username)}
                  onMouseEnter={() => setHighlight(i)}
                >
                  <span>@{u.username}</span>
                  {currentUsername === u.username && (
                    <span className={styles.optionTag}>current</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
        <button
          type="button"
          className={styles.btnGhost}
          onClick={() => submitWith(query.trim())}
          disabled={!query.trim() || loading || !!error}
        >
          sign in
        </button>
      </div>

      {loading && <LoadingBlock label="Loading users" />}
      {error && <ErrorBlock error={error} onRetry={onRetry} />}
      {pickError && (
        <div className={styles.error} role="alert">
          {pickError}
        </div>
      )}
    </div>
  );
}
