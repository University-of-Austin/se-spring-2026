import { useMemo, useState } from "react";
import {
  addReaction,
  listReactions,
  removeReactions,
} from "../api/reactions";
import { useFetch } from "../hooks/useFetch";
import { useToast } from "../hooks/useToast";
import { ApiError } from "../api/types";
import styles from "./ReactionBar.module.css";

const QUICK = ["👍", "❤️", "😂", "🎉", "👀", "🔥"];

type Counts = Map<string, { count: number; mine: boolean }>;

function tally(
  reactions: Array<{ kind: string; username: string }>,
  me: string | null,
): Counts {
  const out: Counts = new Map();
  for (const r of reactions) {
    const curr = out.get(r.kind) ?? { count: 0, mine: false };
    out.set(r.kind, {
      count: curr.count + 1,
      mine: curr.mine || r.username === me,
    });
  }
  return out;
}

export function ReactionBar({
  postId,
  currentUser,
}: {
  postId: number;
  currentUser: string | null;
}) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const { show } = useToast();
  const { data, loading, error, refetch } = useFetch(
    () => listReactions(postId),
    [postId],
  );

  const counts = useMemo(
    () => tally(data ?? [], currentUser),
    [data, currentUser],
  );

  const toggle = async (kind: string) => {
    if (!currentUser) {
      show("Sign in to react.", "info");
      return;
    }
    const existing = counts.get(kind);
    setPickerOpen(false);
    try {
      if (existing?.mine) {
        // The API deletes ALL of a user's reactions on a post in one call,
        // not just one kind. We accept that and refetch.
        await removeReactions(postId, currentUser);
      } else {
        await addReaction(postId, currentUser, kind);
      }
      refetch();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        // already reacted with this kind — refetch to sync UI
        refetch();
      } else {
        show(e instanceof ApiError ? e.detail : String(e), "error");
      }
    }
  };

  if (error && error.status !== 0) return null; // quiet failure — reactions are non-essential
  if (loading && !data) {
    return <div className={styles.bar} aria-hidden="true" />;
  }

  return (
    <div className={styles.bar}>
      {[...counts.entries()].map(([kind, { count, mine }]) => (
        <button
          key={kind}
          type="button"
          className={`${styles.pill} ${mine ? styles.mine : ""}`}
          onClick={() => toggle(kind)}
          aria-label={`${count} ${kind} reaction${count === 1 ? "" : "s"}${
            mine ? ", you reacted" : ""
          }`}
        >
          <span>{kind}</span>
          <span className={styles.count}>{count}</span>
        </button>
      ))}
      <div className={styles.addWrap}>
        <button
          type="button"
          className={`${styles.pill} ${styles.addBtn}`}
          onClick={() => setPickerOpen((o) => !o)}
          aria-expanded={pickerOpen}
          aria-haspopup="true"
          aria-label="Add a reaction"
          title="Add a reaction"
        >
          +
        </button>
        {pickerOpen && (
          <div className={styles.picker} role="menu">
            {QUICK.map((k) => (
              <button
                key={k}
                type="button"
                role="menuitem"
                className={styles.pickerItem}
                onClick={() => toggle(k)}
                aria-label={`React with ${k}`}
              >
                {k}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
