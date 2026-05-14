type Kind = "heart" | "laugh" | "fire";
const KINDS: Array<{ kind: Kind; emoji: string }> = [
  { kind: "heart", emoji: "♥" },
  { kind: "laugh", emoji: "😂" },
  { kind: "fire", emoji: "🔥" },
];

type Props = {
  postId: number;
  counts: Record<string, number>;
  canReact: boolean;
  onReact: (kind: Kind) => Promise<void>;
};

export default function ReactionBar({ counts, canReact, onReact }: Props) {
  return (
    <div className="flex gap-1 mt-2">
      {KINDS.map(({ kind, emoji }) => (
        <button
          key={kind}
          aria-label={kind}
          disabled={!canReact}
          onClick={() => void onReact(kind)}
          className="text-xs border border-border rounded px-2 py-0.5 hover:bg-accent disabled:opacity-50"
        >
          <span aria-hidden className="mr-1">{emoji}</span>
          <span>{counts[kind] ?? 0}</span>
        </button>
      ))}
    </div>
  );
}
