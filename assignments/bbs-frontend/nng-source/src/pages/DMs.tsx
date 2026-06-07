import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { Avatar } from "../components/Avatar";
import { ErrorBox } from "../components/ErrorBox";
import { Spinner } from "../components/Spinner";
import type { DMConversation } from "../types";

function shortTimestamp(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const now = new Date();
  const sameDay =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();
  const pad = (n: number) => String(n).padStart(2, "0");
  if (sameDay) return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function DMs() {
  const { token, username } = useAuth();
  const navigate = useNavigate();
  const [convos, setConvos] = useState<DMConversation[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toUsername, setToUsername] = useState("");

  const load = useCallback(async () => {
    if (!token) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    try {
      const data = await api.listDMs(token);
      setConvos(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load DMs.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  if (!username || !token) {
    return (
      <div className="page page-dms">
        <h1>Direct Messages</h1>
        <p className="empty-state">Log in to read and send DMs.</p>
      </div>
    );
  }

  function startNew(e: React.FormEvent) {
    e.preventDefault();
    const target = toUsername.trim();
    if (!target) return;
    navigate(`/dms/${encodeURIComponent(target)}`);
  }

  return (
    <div className="page page-dms">
      <h1>Direct Messages</h1>

      <form onSubmit={startNew} className="dm-new-form" aria-label="Start a new conversation">
        <label htmlFor="dm-to" className="visually-hidden">Username</label>
        <input
          id="dm-to"
          type="text"
          placeholder="Message a user by username..."
          value={toUsername}
          onChange={(e) => setToUsername(e.target.value)}
        />
        <button type="submit" className="btn btn-primary btn-sm" disabled={!toUsername.trim()}>
          Open chat
        </button>
      </form>

      {loading && <Spinner label="Loading conversations..." />}
      {error && <ErrorBox message={error} onRetry={load} />}
      {convos && convos.length === 0 && (
        <p className="empty-state">No conversations yet. Type a username above to start one.</p>
      )}
      {convos && convos.length > 0 && (
        <ul className="dm-convo-list" aria-label="Conversations">
          {convos.map((c) => (
            <li key={c.partner.username} className="dm-convo-item">
              <Link to={`/dms/${encodeURIComponent(c.partner.username)}`}>
                <Avatar
                  username={c.partner.username}
                  src={c.partner.avatar_url}
                  size="md"
                />
                <div className="dm-convo-body">
                  <div className="dm-convo-header">
                    <span className="dm-convo-name">{c.partner.username}</span>
                    <span className="dm-convo-time">
                      {shortTimestamp(c.last_message.created_at)}
                    </span>
                  </div>
                  <div className="dm-convo-preview">
                    {c.last_message.from_me && <span className="dm-prefix">you: </span>}
                    {c.last_message.message}
                  </div>
                </div>
                {c.unread_count > 0 && (
                  <span className="dm-unread-badge" aria-label={`${c.unread_count} unread`}>
                    {c.unread_count}
                  </span>
                )}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
