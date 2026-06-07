import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div style={{ textAlign: "center", padding: "var(--s-8) 0" }}>
      <h1 style={{ fontSize: "var(--f-3xl)" }}>404</h1>
      <p className="muted">This page doesn't exist.</p>
      <p style={{ marginTop: "var(--s-4)" }}>
        <Link to="/" className="btn">
          ← Back to feed
        </Link>
      </p>
    </div>
  );
}
