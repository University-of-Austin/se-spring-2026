import { useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "@/api/client";
import type { Post, ApiError } from "@/api/types";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import UserPill from "./UserPill";
import ReactionBar from "./ReactionBar";
import ComposeBox from "./ComposeBox";

type Props = {
  post: Post;
  pending?: boolean;
};

type Kind = "heart" | "laugh" | "fire";

function fmtTime(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export default function PostCard({ post, pending = false }: Props) {
  const { username } = useCurrentUser();
  const [counts, setCounts] = useState(post.reaction_counts);
  const [myKind, setMyKind] = useState<Kind | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showReply, setShowReply] = useState(false);

  async function onReact(kind: Kind) {
    if (kind === myKind) return; // A2 POST is idempotent on same kind
    const prevCounts = counts;
    const prevMyKind = myKind;
    const next = { ...counts };
    if (myKind) {
      next[myKind] = Math.max(0, (next[myKind] ?? 0) - 1);
    }
    next[kind] = (next[kind] ?? 0) + 1;
    setCounts(next);
    setMyKind(kind);
    setError(null);
    try {
      await apiFetch(`/posts/${post.id}/reactions`, {
        method: "POST",
        body: JSON.stringify({ kind }),
      });
      const updated = await apiFetch<Post>(`/posts/${post.id}`);
      setCounts(updated.reaction_counts);
    } catch (e) {
      setCounts(prevCounts);
      setMyKind(prevMyKind);
      setError(`Couldn't react: ${(e as ApiError).status}`);
    }
  }

  async function onReply(message: string) {
    await apiFetch("/posts", {
      method: "POST",
      body: JSON.stringify({ message, parent_id: post.id }),
    });
    setShowReply(false);
  }

  return (
    <article
      className={`border border-border rounded-lg bg-card px-4 py-3 transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 ${pending ? "anim-optimistic-in" : ""}`}
    >
      <header className="flex items-center gap-2 text-sm text-muted-foreground">
        <UserPill username={post.username} />
        <span aria-hidden>·</span>
        <span>{fmtTime(post.created_at)}</span>
        {post.board && (
          <>
            <span aria-hidden>·</span>
            <Link to={`/boards/${post.board}`} className="hover:underline">
              #{post.board}
            </Link>
          </>
        )}
        {!pending && username && (
          <button
            onClick={() => setShowReply((v) => !v)}
            className="ml-auto text-xs underline hover:text-foreground"
          >
            {showReply ? "cancel" : "reply"}
          </button>
        )}
        {pending && (
          <span className="ml-auto text-xs italic text-muted-foreground">
            posting…
          </span>
        )}
      </header>

      <p className="mt-2 whitespace-pre-wrap text-base text-foreground">
        {post.message}
      </p>

      {!pending && (
        <div className="mt-2 flex items-center gap-3">
          <ReactionBar
            postId={post.id}
            counts={counts}
            canReact={Boolean(username)}
            onReact={onReact}
          />
          <Link
            to={`/posts/${post.id}`}
            className="ml-auto text-xs text-muted-foreground hover:text-foreground hover:underline"
          >
            View thread →
          </Link>
        </div>
      )}

      <div
        className={`grid mt-3 transition-[grid-template-rows] duration-200 ease-in-out ${showReply ? "grid-rows-[1fr]" : "grid-rows-[0fr] mt-0"}`}
      >
        <div className="overflow-hidden">
          <ComposeBox
            buttonLabel="Reply"
            placeholder={`Reply to @${post.username}…`}
            onSubmit={onReply}
          />
        </div>
      </div>

      {error && (
        <p role="alert" className="text-xs text-destructive mt-1">
          {error}
        </p>
      )}
    </article>
  );
}
