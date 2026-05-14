import { useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "@/api/client";
import type { Post, ApiError } from "@/api/types";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import UserPill from "./UserPill";
import ReactionBar from "./ReactionBar";

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
  const [error, setError] = useState<string | null>(null);

  async function onReact(kind: Kind) {
    const prev = counts;
    setCounts({ ...counts, [kind]: (counts[kind] ?? 0) + 1 });
    setError(null);
    try {
      await apiFetch(`/posts/${post.id}/reactions`, { method: "POST", body: JSON.stringify({ kind }) });
    } catch (e) {
      setCounts(prev);
      setError(`Couldn't react: ${(e as ApiError).status}`);
    }
  }

  return (
    <article className={`border border-neutral-200 rounded-lg bg-white px-4 py-3 ${pending ? "opacity-60" : ""}`}>
      <header className="flex items-center gap-2 text-sm text-neutral-500">
        <UserPill username={post.username} />
        <span aria-hidden>·</span>
        <Link to={`/posts/${post.id}`} className="hover:underline">{fmtTime(post.created_at)}</Link>
        {post.board && (
          <>
            <span aria-hidden>·</span>
            <Link to={`/boards/${post.board}`} className="hover:underline">#{post.board}</Link>
          </>
        )}
        {pending && <span className="ml-auto text-xs italic text-neutral-400">posting…</span>}
      </header>
      <p className="mt-2 whitespace-pre-wrap text-base">{post.message}</p>
      {!pending && (
        <ReactionBar postId={post.id} counts={counts} canReact={Boolean(username)} onReact={onReact} />
      )}
      {error && <p role="alert" className="text-xs text-red-700 mt-1">{error}</p>}
    </article>
  );
}
