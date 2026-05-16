import { Link } from "react-router-dom";
import { api } from "../api";
import { ErrorBox } from "../components/ErrorBox";
import { Spinner } from "../components/Spinner";
import { useAsync } from "../hooks/useAsync";

export function Boards() {
  const { data, loading, error, reload } = useAsync(() => api.listBoards(), []);

  // Sort by post_count desc, but keep "general" at the top if it exists.
  const sorted = data
    ? [...data].sort((a, b) => {
        if (a.name === "general") return -1;
        if (b.name === "general") return 1;
        return b.post_count - a.post_count;
      })
    : null;

  return (
    <div className="page page-boards">
      <h1>Boards</h1>
      <p className="page-subtitle">
        Posts are organized by board. Anyone can post to any board, and creating a new
        board is as simple as posting to a name no one's used yet.
      </p>

      {loading && <Spinner label="Loading boards..." />}
      {error && <ErrorBox message={error} onRetry={reload} />}
      {sorted && sorted.length === 0 && (
        <p className="empty-state">No boards yet. Be the first to post.</p>
      )}
      {sorted && sorted.length > 0 && (
        <ul className="board-list" aria-label="Boards">
          {sorted.map((b) => (
            <li key={b.name} className="board-list-item">
              <Link to={`/?board=${encodeURIComponent(b.name)}`}>
                <span className="board-name">#{b.name}</span>
                <span className="board-meta">
                  {b.post_count} {b.post_count === 1 ? "post" : "posts"}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
