import { useParams } from "react-router-dom";
import { useApi } from "@/hooks/useApi";
import LoadingRow from "@/components/LoadingRow";
import ErrorBox from "@/components/ErrorBox";
import PostCard from "@/components/PostCard";
import type { Post, User } from "@/api/types";

export default function UserPage() {
  const { username = "" } = useParams();
  const user = useApi<User>(`/users/${username}`);
  const posts = useApi<Post[]>(`/users/${username}/posts`);

  if (user.error?.status === 404) {
    return <p className="py-12 text-center text-neutral-500">User <code>{username}</code> not found.</p>;
  }
  if (user.loading || posts.loading) return <LoadingRow />;
  if (user.error) return <ErrorBox error={user.error} onRetry={user.refetch} />;
  if (posts.error) return <ErrorBox error={posts.error} onRetry={posts.refetch} />;
  if (!user.data) return null;

  return (
    <div className="space-y-4">
      <header className="border border-neutral-200 rounded-lg bg-white px-4 py-3">
        <h1 className="text-xl font-semibold">{user.data.username}</h1>
        <p className="text-sm text-neutral-500">
          Joined {new Date(user.data.created_at).toLocaleDateString()} · {user.data.post_count} posts
        </p>
        {user.data.bio && <p className="mt-2 text-base whitespace-pre-wrap">{user.data.bio}</p>}
      </header>

      {posts.data && posts.data.length > 0 ? (
        posts.data.map((p) => <PostCard key={p.id} post={p} />)
      ) : (
        <p className="py-8 text-center text-neutral-500">No posts yet.</p>
      )}
    </div>
  );
}
