import { useParams } from "react-router-dom";
import { useFeed } from "@/hooks/useFeed";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import LoadingRow from "@/components/LoadingRow";
import ErrorBox from "@/components/ErrorBox";
import PostCard from "@/components/PostCard";
import ComposeBox from "@/components/ComposeBox";

export default function BoardPage() {
  const { name = "" } = useParams();
  const { username } = useCurrentUser();
  const { posts, optimistic, loading, error, hasMore, loadMore, refetch, createPost } = useFeed({ board: name });

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">#{name}</h1>
      {username && <ComposeBox onSubmit={(m) => createPost(m, name)} placeholder={`Post to #${name}…`} />}
      {error && <ErrorBox error={error} onRetry={refetch} />}
      {loading && posts.length === 0 ? (
        <LoadingRow />
      ) : (
        <>
          {optimistic.map((p) => <PostCard key={`opt-${p.client_id}`} post={p} pending />)}
          {posts.length === 0 && optimistic.length === 0 && !error && (
            <p className="py-12 text-center text-neutral-500">No posts on this board yet.</p>
          )}
          {posts.map((p) => <PostCard key={p.id} post={p} />)}
          {hasMore && (
            <button onClick={loadMore} className="w-full border border-neutral-200 rounded-lg bg-white py-2 text-sm hover:bg-neutral-50">
              Load more
            </button>
          )}
        </>
      )}
    </div>
  );
}
