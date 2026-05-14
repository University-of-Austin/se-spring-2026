import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "@/api/client";
import { useApi } from "@/hooks/useApi";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import LoadingRow from "@/components/LoadingRow";
import ErrorBox from "@/components/ErrorBox";
import { type ApiError, formatDetail } from "@/api/types";
import type { Board } from "@/api/types";

const NAME_RE = /^[a-zA-Z0-9_-]+$/;

function CreateBoardForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const valid = NAME_RE.test(name) && name.length >= 1 && name.length <= 30;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!valid || busy) return;
    setBusy(true);
    setError(null);
    try {
      await apiFetch("/boards", {
        method: "POST",
        body: JSON.stringify({ name, description: description || null }),
      });
      setName("");
      setDescription("");
      onCreated();
    } catch (e) {
      setError(formatDetail((e as ApiError).detail));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className="border border-border rounded-lg bg-card p-3 space-y-2"
    >
      <h2 className="text-sm font-medium text-foreground">Create a board</h2>
      <div className="flex flex-col sm:flex-row gap-2">
        <div className="flex-1 space-y-1">
          <label htmlFor="board-name" className="sr-only">Name</label>
          <input
            id="board-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="board-name"
            className="w-full border border-input rounded px-3 py-2 text-sm bg-background"
          />
        </div>
        <div className="flex-1 space-y-1">
          <label htmlFor="board-desc" className="sr-only">Description</label>
          <input
            id="board-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="optional description"
            className="w-full border border-input rounded px-3 py-2 text-sm bg-background"
          />
        </div>
        <button
          type="submit"
          disabled={!valid || busy}
          className="bg-primary text-primary-foreground text-sm px-3 py-2 rounded disabled:opacity-50"
        >
          {busy ? "Creating…" : "Create"}
        </button>
      </div>
      <p className="text-xs text-muted-foreground">
        Letters, digits, underscores, dashes. No spaces.
      </p>
      {error && (
        <p role="alert" className="text-xs text-destructive">{error}</p>
      )}
    </form>
  );
}

export default function BoardsPage() {
  const { username } = useCurrentUser();
  const { data, loading, error, refetch } = useApi<Board[]>("/boards");

  return (
    <div className="space-y-4">
      {username ? (
        <CreateBoardForm onCreated={refetch} />
      ) : (
        <div className="border border-border rounded-lg bg-card p-3 text-sm text-muted-foreground">
          <Link to="/login" className="underline">Sign in</Link> to create a board.
        </div>
      )}

      {loading && <LoadingRow />}
      {error && <ErrorBox error={error} onRetry={refetch} />}
      {!loading && !error && data && data.length === 0 && (
        <p className="py-12 text-center text-muted-foreground">No boards yet.</p>
      )}
      {data && data.length > 0 && (
        <ul className="divide-y divide-border border border-border rounded-lg bg-card">
          {data.map((b) => (
            <li key={b.name} className="px-4 py-3">
              <Link to={`/boards/${b.name}`} className="font-medium hover:underline">#{b.name}</Link>
              <span className="text-sm text-muted-foreground ml-2">{b.post_count} posts</span>
              {b.description && <p className="text-sm text-muted-foreground mt-1">{b.description}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
