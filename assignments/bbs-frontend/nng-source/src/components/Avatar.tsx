import { useState } from "react";
import { resolveBackendUrl } from "../api";

interface AvatarProps {
  username: string;
  /** Path or URL from the backend (e.g. "/static/avatars/3.png"). null = fallback. */
  src: string | null;
  size?: "xs" | "sm" | "md" | "lg" | "xl";
}

// Deterministic color from the username so the fallback initial has some variety.
// Hash to one of N curated hues; saturation/lightness fixed so it always reads
// against dark and light themes.
const PALETTE = [
  "#5cf0e6", "#a48cff", "#f0a060", "#f06c9c", "#a0e066",
  "#80d4ff", "#ffd060", "#ff8080", "#80ffc0", "#c8a0ff",
];

function colorFor(username: string): string {
  let hash = 0;
  for (let i = 0; i < username.length; i++) {
    hash = (hash * 31 + username.charCodeAt(i)) >>> 0;
  }
  return PALETTE[hash % PALETTE.length];
}

export function Avatar({ username, src, size = "sm" }: AvatarProps) {
  const [failed, setFailed] = useState(false);
  const url = resolveBackendUrl(src);
  const showImage = url && !failed;
  const initial = (username[0] || "?").toUpperCase();

  return (
    <span
      className={`avatar avatar-${size}`}
      aria-hidden="true"
      style={showImage ? undefined : { background: colorFor(username), color: "#0a0a14" }}
    >
      {showImage ? (
        <img
          src={url}
          alt=""
          className="avatar-img"
          loading="lazy"
          onError={() => setFailed(true)}
        />
      ) : (
        <span className="avatar-initial">{initial}</span>
      )}
    </span>
  );
}
