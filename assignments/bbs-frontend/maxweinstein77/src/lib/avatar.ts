// Deterministic avatar color from a username. Same name always gets the
// same color so avatars are recognizable across components.

const PALETTE = [
  "#f97316", "#22c55e", "#3b82f6", "#a855f7",
  "#ec4899", "#eab308", "#06b6d4", "#ef4444",
];

export function avatarColor(username: string): string {
  // Simple deterministic string hash; reduce per lecture 5.1 idiom guidance.
  const hash = [...username].reduce(
    (acc, ch) => ((acc << 5) - acc + ch.charCodeAt(0)) | 0,
    0,
  );
  return PALETTE[Math.abs(hash) % PALETTE.length];
}

export function avatarInitial(username: string): string {
  return username[0]?.toUpperCase() ?? "?";
}
