import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiFetch } from "@/api/client";
import { useApi } from "@/hooks/useApi";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import LoadingRow from "@/components/LoadingRow";
import ErrorBox from "@/components/ErrorBox";
import PostCard from "@/components/PostCard";
import { type ApiError, formatDetail } from "@/api/types";
import type { Post, User } from "@/api/types";

export default function UserPage() {
  const { username = "" } = useParams();
  const navigate = useNavigate();
  const { username: currentUser, clearUsername } = useCurrentUser();
  const user = useApi<User>(`/users/${username}`);
  const posts = useApi<Post[]>(`/users/${username}/posts`);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const isOwnProfile = currentUser !== null && currentUser === username;

  async function onDelete() {
    if (!window.confirm("Delete your account? This cannot be undone. Your existing posts will remain but show as [deleted].")) {
      return;
    }
    setDeleting(true);
    setDeleteError(null);
    try {
      await apiFetch(`/users/${username}`, { method: "DELETE" });
      clearUsername();
      navigate("/");
    } catch (e) {
      setDeleteError(formatDetail((e as ApiError).detail));
      setDeleting(false);
    }
  }

  if (user.error?.status === 404) {
    return <p className="py-12 text-center text-muted-foreground">User <code>{username}</code> not found.</p>;
  }
  if (user.loading || posts.loading) return <LoadingRow />;
  if (user.error) return <ErrorBox error={user.error} onRetry={user.refetch} />;
  if (posts.error) return <ErrorBox error={posts.error} onRetry={posts.refetch} />;
  if (!user.data) return null;

  return (
    <div className="space-y-4">
      <header className="border border-border rounded-lg bg-card px-4 py-3">
        <h1 className="text-xl font-semibold text-foreground">{user.data.username}</h1>
        <p className="text-sm text-muted-foreground">
          Joined {new Date(user.data.created_at).toLocaleDateString()} · {user.data.post_count} posts
        </p>
        {user.data.bio && (
          <p className="mt-2 text-base whitespace-pre-wrap text-foreground">{user.data.bio}</p>
        )}
        {isOwnProfile && (
          <div className="mt-3 pt-3 border-t border-border flex items-center gap-3">
            <button
              onClick={onDelete}
              disabled={deleting}
              className="text-xs text-destructive underline hover:no-underline disabled:opacity-50"
            >
              {deleting ? "Deleting…" : "Delete account"}
            </button>
            {deleteError && (
              <span role="alert" className="text-xs text-destructive">{deleteError}</span>
            )}
          </div>
        )}
      </header>

      {posts.data && posts.data.length > 0 ? (
        posts.data.map((p) => <PostCard key={p.id} post={p} />)
      ) : (
        <p className="py-8 text-center text-muted-foreground">No posts yet.</p>
      )}
    </div>
  );
}
