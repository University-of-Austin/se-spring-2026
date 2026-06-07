import { useState } from "react";
import { useParams } from "react-router-dom";
import { useFeed } from "@/hooks/useFeed";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import LoadingRow from "@/components/LoadingRow";
import ErrorBox from "@/components/ErrorBox";
import PostCard from "@/components/PostCard";
import ComposeBox from "@/components/ComposeBox";

type Sort = "newest" | "oldest" | "trending";

export default function BoardPage() {
  const { name = "" } = useParams();
  const { username } = useCurrentUser();
  const [sort, setSort] = useState<Sort>("newest");
  const { posts, optimistic, loading, error, hasMore, loadMore, refetch, createPost } = useFeed({ board: name, sort });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">#{name}</h1>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as Sort)}
          className="border border-input rounded px-2 py-1 text-sm bg-background"
          aria-label="Sort"
        >
          <option value="newest">Newest</option>
          <option value="oldest">Oldest</option>
          <option value="trending">Trending</option>
        </select>
      </div>
      {username && <ComposeBox onSubmit={(m) => createPost(m, name)} placeholder={`Post to #${name}…`} />}
      {error && <ErrorBox error={error} onRetry={refetch} />}
      {loading && posts.length === 0 ? (
        <LoadingRow />
      ) : (
        <>
          {optimistic.map((p) => <PostCard key={`opt-${p.client_id}`} post={p} pending />)}
          {posts.length === 0 && optimistic.length === 0 && !error && (
            <p className="py-12 text-center text-muted-foreground">No posts on this board yet.</p>
          )}
          {posts.map((p) => <PostCard key={p.id} post={p} />)}
          {hasMore && (
            <button onClick={loadMore} className="w-full border border-border rounded-lg bg-card py-2 text-sm hover:bg-accent">
              Load more
            </button>
          )}
        </>
      )}
    </div>
  );
}
