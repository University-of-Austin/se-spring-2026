import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="page">
      <h1>404</h1>
      <p>That route does not exist.</p>
      <p>
        <Link to="/">← Back to feed</Link>
      </p>
    </div>
  );
}
