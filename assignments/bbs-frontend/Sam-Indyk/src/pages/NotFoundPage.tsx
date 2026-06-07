import { Link } from "react-router-dom";
import { EmptyState } from "../components/EmptyState";

export function NotFoundPage() {
  return (
    <EmptyState
      title="404 — Page not found"
      description="That URL doesn't exist in this app."
      action={
        <Link to="/" className="btn">
          Back to feed
        </Link>
      }
    />
  );
}
