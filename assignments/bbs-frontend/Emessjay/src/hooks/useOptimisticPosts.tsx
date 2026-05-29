// Optimistic POST support.
//
// The flow:
//   1. ComposeView calls addPending(message, username) and gets a
//      tempId.  An entry appears in `pending` with status 'pending'.
//      Compose immediately navigates to the feed.
//   2. FeedView reads `pending` from this context and renders pending
//      entries above the server posts, in a muted "sending…" style.
//   3. ComposeView's createPost() promise resolves.  It calls
//      resolvePending(tempId, ...).  On success the entry transitions
//      to 'confirmed' for a brief window so the user doesn't see a
//      gap, *and* `feedVersion` bumps — which is wired into usePosts
//      deps so the feed refetches.  When the refetch returns, the
//      real post is in the list; we remove the confirmed entry via
//      a 1.5s timeout so the visual hand-off looks intentional.
//   4. On failure the entry transitions to 'failed' with the error
//      detail.  The feed renders it with a red border + a retry /
//      dismiss button.  feedVersion does NOT bump; no refetch.
//
// The point of doing this in a context (rather than locally in
// FeedView) is that the API call survives the unmount of
// ComposeView when we navigate away.  Without this, navigating
// before the promise resolves would orphan the result.

import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { createPost } from "../api/endpoints";
import { ApiError } from "../api/client";

export type PendingStatus = "pending" | "confirmed" | "failed";

export type PendingPost = {
  tempId: number;
  message: string;
  username: string;
  createdAt: string;
  status: PendingStatus;
  errorDetail?: string;
  // Real server id, set once createPost resolves.  FeedView uses it
  // to drop the pending entry the instant the refetched feed
  // contains the matching post, so the optimistic and live rows
  // never both appear.
  confirmedId?: number;
};

type Ctx = {
  pending: PendingPost[];
  feedVersion: number;
  submit: (message: string, username: string) => Promise<{ ok: boolean }>;
  retry: (tempId: number) => Promise<{ ok: boolean }>;
  dismiss: (tempId: number) => void;
};

const OptimisticPostsContext = createContext<Ctx | null>(null);

const CONFIRMED_VISIBLE_MS = 1500;

export function OptimisticPostsProvider({ children }: { children: ReactNode }) {
  const [pending, setPending] = useState<PendingPost[]>([]);
  const [feedVersion, setFeedVersion] = useState(0);
  // Counter for generating unique negative tempIds — never collides
  // with real positive post IDs from the server.
  const nextId = useRef(-1);

  const startSubmission = useCallback(
    async (entry: PendingPost): Promise<{ ok: boolean }> => {
      try {
        const created = await createPost(entry.message, entry.username);
        // Confirm: record the real id so FeedView can swap us out the
        // moment the refetch returns, bump feedVersion to trigger that
        // refetch, and keep a timeout as a fallback in case the refetch
        // is slow or fails.
        setPending((p) =>
          p.map((x) =>
            x.tempId === entry.tempId
              ? { ...x, status: "confirmed", confirmedId: created.id }
              : x,
          ),
        );
        setFeedVersion((v) => v + 1);
        setTimeout(() => {
          setPending((p) => p.filter((x) => x.tempId !== entry.tempId));
        }, CONFIRMED_VISIBLE_MS);
        return { ok: true };
      } catch (err) {
        const detail = err instanceof ApiError ? err.detail : "Failed to post";
        setPending((p) =>
          p.map((x) =>
            x.tempId === entry.tempId ? { ...x, status: "failed", errorDetail: detail } : x,
          ),
        );
        return { ok: false };
      }
    },
    [],
  );

  const submit = useCallback(
    async (message: string, username: string) => {
      const tempId = nextId.current--;
      const entry: PendingPost = {
        tempId,
        message,
        username,
        createdAt: new Date().toISOString(),
        status: "pending",
      };
      setPending((p) => [entry, ...p]);
      return startSubmission(entry);
    },
    [startSubmission],
  );

  const retry = useCallback(
    async (tempId: number) => {
      let target: PendingPost | undefined;
      setPending((p) =>
        p.map((x) => {
          if (x.tempId === tempId) {
            target = { ...x, status: "pending", errorDetail: undefined };
            return target;
          }
          return x;
        }),
      );
      if (!target) return { ok: false };
      return startSubmission(target);
    },
    [startSubmission],
  );

  const dismiss = useCallback((tempId: number) => {
    setPending((p) => p.filter((x) => x.tempId !== tempId));
  }, []);

  const value = useMemo<Ctx>(
    () => ({ pending, feedVersion, submit, retry, dismiss }),
    [pending, feedVersion, submit, retry, dismiss],
  );

  return <OptimisticPostsContext.Provider value={value}>{children}</OptimisticPostsContext.Provider>;
}

export function useOptimisticPosts(): Ctx {
  const ctx = useContext(OptimisticPostsContext);
  if (!ctx) throw new Error("useOptimisticPosts must be used inside <OptimisticPostsProvider>");
  return ctx;
}
