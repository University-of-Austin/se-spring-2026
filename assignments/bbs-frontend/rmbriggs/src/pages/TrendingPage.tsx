import { useFeed } from "@/hooks/useFeed";
import LoadingRow from "@/components/LoadingRow";
import ErrorBox from "@/components/ErrorBox";
import PostCard from "@/components/PostCard";

export default function TrendingPage() {
  const { posts, loading, error, refetch } = useFeed({ sort: "trending" });

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-semibold text-foreground">Trending</h1>
        <p className="text-sm text-muted-foreground">Posts ranked by total reactions.</p>
      </header>

      {error && <ErrorBox error={error} onRetry={refetch} />}

      {loading && posts.length === 0 ? (
        <LoadingRow />
      ) : posts.length === 0 && !error ? (
        <p className="py-12 text-center text-muted-foreground">No posts yet.</p>
      ) : (
        posts.map((p) => <PostCard key={p.id} post={p} />)
      )}
    </div>
  );
}
