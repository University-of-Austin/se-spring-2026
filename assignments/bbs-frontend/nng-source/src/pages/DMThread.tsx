import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { ApiError, type DMMessage, type DMThread as DMThreadShape } from "../types";
import { useAuth } from "../auth";
import { Avatar } from "../components/Avatar";
import { ErrorBox } from "../components/ErrorBox";
import { Spinner } from "../components/Spinner";

const POLL_INTERVAL_MS = 4000;
const MAX_MSG_LEN = 2000;

function formatTime(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

let placeholderId = -1;

export function DMThread() {
  const { username } = useParams<{ username: string }>();
  const me = useAuth();
  const partner = username ?? "";

  const [data, setData] = useState<DMThreadShape | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const isPolling = useRef(false);
  const listEndRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async (silent = false) => {
    if (!me.token || !partner) return;
    if (!silent) setLoading(true);
    if (!silent) setError(null);
    setNotFound(false);
    try {
      const t = await api.getDMThread(partner, me.token);
      setData(t);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) setNotFound(true);
      else if (!silent) {
        setError(err instanceof Error ? err.message : "Could not load conversation.");
      }
    } finally {
      if (!silent) setLoading(false);
    }
  }, [me.token, partner]);

  useEffect(() => { void load(); }, [load]);

  // Auto-scroll to the bottom on initial load and whenever new messages arrive.
  useEffect(() => {
    listEndRef.current?.scrollIntoView({ block: "end" });
  }, [data?.messages.length]);

  // Light polling so incoming messages show up without a refresh.
  useEffect(() => {
    if (loading || error || notFound) return;
    const id = setInterval(async () => {
      if (isPolling.current || document.hidden) return;
      isPolling.current = true;
      try { await load(true); } finally { isPolling.current = false; }
    }, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [load, loading, error, notFound]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || !me.token || sending) return;
    if (trimmed.length > MAX_MSG_LEN) return;
    setSending(true);
    setError(null);

    const tempId = placeholderId--;
    const optimistic: DMMessage = {
      id: tempId,
      from_username: me.username!,
      to_username: partner,
      from_me: true,
      message: trimmed,
      created_at: new Date().toISOString(),
      read_at: null,
    };
    setData((prev) => prev ? { ...prev, messages: [...prev.messages, optimistic] } : prev);
    setDraft("");

    try {
      const real = await api.sendDM(partner, trimmed, me.token);
      setData((prev) => prev
        ? { ...prev, messages: prev.messages.map((m) => m.id === tempId ? real : m) }
        : prev,
      );
    } catch (err) {
      setData((prev) => prev
        ? { ...prev, messages: prev.messages.filter((m) => m.id !== tempId) }
        : prev,
      );
      setError(err instanceof Error ? err.message : "Could not send message.");
      setDraft(trimmed);
    } finally {
      setSending(false);
    }
  }

  if (!me.username || !me.token) {
    return (
      <div className="page">
        <p className="empty-state">
          Log in to view this conversation.{" "}
          <Link to="/login">Log in</Link>
        </p>
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="page page-notfound">
        <h1>User not found</h1>
        <p>No account exists with username <code>{partner}</code>.</p>
        <Link to="/dms" className="btn btn-secondary">&larr; Back to DMs</Link>
      </div>
    );
  }

  if (loading) return <div className="page"><Spinner label={`Loading chat with ${partner}...`} /></div>;
  if (error) return <div className="page"><ErrorBox message={error} onRetry={() => load()} /></div>;
  if (!data) return null;

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      e.currentTarget.form?.requestSubmit();
    }
  };

  const tooLong = draft.length > MAX_MSG_LEN;

  return (
    <div className="page page-dm-thread">
      <header className="dm-thread-header">
        <Link to="/dms" className="btn btn-link back-link">&larr; All DMs</Link>
        <Link to={`/users/${encodeURIComponent(data.partner.username)}`} className="dm-thread-partner">
          <Avatar username={data.partner.username} src={data.partner.avatar_url} size="md" />
          <span>{data.partner.username}</span>
        </Link>
      </header>

      <div className="dm-message-list" aria-live="polite" aria-atomic="false">
        {data.messages.length === 0 && (
          <p className="empty-state">No messages yet. Say hi!</p>
        )}
        {data.messages.map((m) => (
          <div
            key={m.id < 0 ? `temp-${m.id}` : m.id}
            className={`dm-bubble ${m.from_me ? "dm-bubble-me" : "dm-bubble-them"} ${m.id < 0 ? "dm-bubble-optimistic" : ""}`}
            aria-busy={m.id < 0}
          >
            <p className="dm-bubble-msg">{m.message}</p>
            <span className="dm-bubble-time">{formatTime(m.created_at)}</span>
          </div>
        ))}
        <div ref={listEndRef} />
      </div>

      <form onSubmit={send} className="dm-compose" aria-label={`Message to ${partner}`}>
        <label htmlFor="dm-draft" className="visually-hidden">Message</label>
        <textarea
          id="dm-draft"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={`Message ${partner}... (Cmd/Ctrl+Enter to send)`}
          rows={2}
          maxLength={MAX_MSG_LEN}
          aria-invalid={tooLong}
        />
        <button
          type="submit"
          className="btn btn-primary"
          disabled={sending || !draft.trim() || tooLong}
        >
          {sending ? "Sending..." : "Send"}
        </button>
      </form>
    </div>
  );
}
