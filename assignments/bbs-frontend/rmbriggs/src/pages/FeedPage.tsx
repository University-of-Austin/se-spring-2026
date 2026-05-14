import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useFeed } from "@/hooks/useFeed";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import LoadingRow from "@/components/LoadingRow";
import ErrorBox from "@/components/ErrorBox";
import PostCard from "@/components/PostCard";
import ComposeBox from "@/components/ComposeBox";

type Sort = "newest" | "oldest" | "trending";

export default function FeedPage() {
  const { username } = useCurrentUser();
  const [qInput, setQInput] = useState("");
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<Sort>("newest");
  const searchRef = useRef<HTMLInputElement>(null);
  const { posts, optimistic, loading, error, hasMore, loadMore, refetch, createPost } = useFeed({
    sort,
    ...(q ? { q } : {}),
  });

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "/" && !(e.target instanceof HTMLInputElement) && !(e.target instanceof HTMLTextAreaElement)) {
        e.preventDefault();
        searchRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 items-center">
        <label htmlFor="search" className="sr-only">Search posts</label>
        <input
          id="search"
          ref={searchRef}
          value={qInput}
          onChange={(e) => setQInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") setQ(qInput); }}
          placeholder="Search posts (press / to focus)"
          className="flex-1 min-w-[200px] border border-input rounded px-3 py-2 text-sm bg-background"
        />
        <button
          onClick={() => setQ(qInput)}
          className="border border-input rounded px-3 py-2 text-sm hover:bg-accent transition-colors"
        >
          Search
        </button>
        {q && (
          <button
            onClick={() => { setQ(""); setQInput(""); }}
            className="text-sm underline text-muted-foreground"
          >
            Clear
          </button>
        )}
        <label htmlFor="sort" className="sr-only">Sort</label>
        <select
          id="sort"
          value={sort}
          onChange={(e) => setSort(e.target.value as Sort)}
          className="border border-input rounded px-2 py-2 text-sm bg-background"
        >
          <option value="newest">Newest</option>
          <option value="oldest">Oldest</option>
          <option value="trending">Trending</option>
        </select>
      </div>

      {username ? (
        <ComposeBox onSubmit={(msg) => createPost(msg)} />
      ) : (
        <div className="border border-border rounded-lg bg-card p-3 text-sm text-muted-foreground">
          <Link to="/login" className="underline">Sign in</Link> to post.
        </div>
      )}

      {error && <ErrorBox error={error} onRetry={refetch} />}

      {loading && posts.length === 0 ? (
        <LoadingRow />
      ) : (
        <>
          {optimistic.map((p) => <PostCard key={`opt-${p.client_id}`} post={p} pending />)}
          {posts.length === 0 && optimistic.length === 0 && !error && (
            <p className="py-12 text-center text-muted-foreground">{q ? "No posts match." : "No posts yet."}</p>
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
