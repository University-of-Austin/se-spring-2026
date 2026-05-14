import { useMemo, useState } from "react";
import type { Post } from "@/api/types";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import UserPill from "./UserPill";
import ComposeBox from "./ComposeBox";

type Node = Post & { children: Node[] };

function buildTree(posts: Post[], rootId: number): Node | null {
  const byId = new Map<number, Node>();
  posts.forEach((p) => byId.set(p.id, { ...p, children: [] }));
  posts.forEach((p) => {
    if (p.parent_id != null) {
      byId.get(p.parent_id)?.children.push(byId.get(p.id)!);
    }
  });
  return byId.get(rootId) ?? null;
}

function PostNode({
  node,
  depth,
  onDelete,
  onReply,
}: {
  node: Node;
  depth: number;
  onDelete: (id: number) => Promise<void>;
  onReply: (message: string, parentId: number) => Promise<void>;
}) {
  const { username } = useCurrentUser();
  const [showReply, setShowReply] = useState(false);
  const indent = Math.min(depth, 5) * 16;

  return (
    <div style={{ marginLeft: indent }} className="space-y-2">
      <article className="border border-neutral-200 rounded-lg bg-white px-4 py-3">
        <header className="flex items-center gap-2 text-sm text-neutral-500">
          <UserPill username={node.username} />
          <span aria-hidden>·</span>
          <span>{new Date(node.created_at).toLocaleString()}</span>
          {username && (
            <button onClick={() => setShowReply((v) => !v)} className="ml-auto text-xs underline">
              {showReply ? "cancel" : "reply"}
            </button>
          )}
          {username === node.username && (
            <button
              onClick={() => onDelete(node.id)}
              className="text-xs text-red-700 underline"
            >
              delete
            </button>
          )}
        </header>
        <p className="mt-2 whitespace-pre-wrap text-base">{node.message}</p>
      </article>
      {showReply && (
        <ComposeBox
          buttonLabel="Reply"
          placeholder="Write a reply…"
          onSubmit={async (m) => {
            await onReply(m, node.id);
            setShowReply(false);
          }}
        />
      )}
      {node.children.map((c) => (
        <PostNode key={c.id} node={c} depth={depth + 1} onDelete={onDelete} onReply={onReply} />
      ))}
    </div>
  );
}

export default function ThreadView({
  posts,
  rootId,
  onDelete,
  onReply,
}: {
  posts: Post[];
  rootId: number;
  onDelete: (id: number) => Promise<void>;
  onReply: (message: string, parentId: number) => Promise<void>;
}) {
  const tree = useMemo(() => buildTree(posts, rootId), [posts, rootId]);
  if (!tree) return <p className="text-neutral-500">Thread root not found.</p>;
  return <PostNode node={tree} depth={0} onDelete={onDelete} onReply={onReply} />;
}
