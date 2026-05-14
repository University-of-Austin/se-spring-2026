import { Link } from "react-router-dom";
import { useApi } from "@/hooks/useApi";
import LoadingRow from "@/components/LoadingRow";
import ErrorBox from "@/components/ErrorBox";
import type { Board } from "@/api/types";

export default function BoardsPage() {
  const { data, loading, error, refetch } = useApi<Board[]>("/boards");

  if (loading) return <LoadingRow />;
  if (error) return <ErrorBox error={error} onRetry={refetch} />;
  if (!data || data.length === 0) return <p className="py-12 text-center text-muted-foreground">No boards yet.</p>;

  return (
    <ul className="divide-y divide-border border border-border rounded-lg bg-card">
      {data.map((b) => (
        <li key={b.name} className="px-4 py-3">
          <Link to={`/boards/${b.name}`} className="font-medium hover:underline">#{b.name}</Link>
          <span className="text-sm text-muted-foreground ml-2">{b.post_count} posts</span>
          {b.description && <p className="text-sm text-muted-foreground mt-1">{b.description}</p>}
        </li>
      ))}
    </ul>
  );
}
