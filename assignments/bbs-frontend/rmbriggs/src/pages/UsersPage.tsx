import { Link } from "react-router-dom";
import { useApi } from "@/hooks/useApi";
import LoadingRow from "@/components/LoadingRow";
import ErrorBox from "@/components/ErrorBox";
import type { User } from "@/api/types";

export default function UsersPage() {
  const { data, loading, error, refetch } = useApi<User[]>("/users");

  if (loading) return <LoadingRow />;
  if (error) return <ErrorBox error={error} onRetry={refetch} />;
  if (!data || data.length === 0) return <p className="py-12 text-center text-muted-foreground">No users yet.</p>;

  return (
    <ul className="divide-y divide-border border border-border rounded-lg bg-card">
      {data.map((u) => (
        <li key={u.username} className="px-4 py-3 flex items-center gap-3">
          <Link to={`/users/${u.username}`} className="font-medium hover:underline">{u.username}</Link>
          <span className="text-sm text-muted-foreground">{u.post_count} posts</span>
        </li>
      ))}
    </ul>
  );
}
