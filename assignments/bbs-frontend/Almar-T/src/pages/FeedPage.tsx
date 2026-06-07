import { useCallback, useEffect, useId, useState } from "react";
import { Composer } from "../components/Composer";
import { ErrorBanner } from "../components/ErrorBanner";
import { LoadMore } from "../components/Pagination";
import { LoadingDots } from "../components/LoadingDots";
import { PostCard } from "../components/PostCard";
import { createPost, deletePost, listPosts } from "../api/posts";
import { ApiError, type Post } from "../api/types";
import { useCurrentUser } from "../hooks/useCurrentUser";
import { useToast } from "../hooks/useToast";
import styles from "./FeedPage.module.css";

const PAGE_SIZE = 20;
const POLL_MS = 5000;

export default function FeedPage() {
  const { currentUser } = useCurrentUser();
  const { show } = useToast();
  const searchId = useId();

  const [searchInput, setSearchInput] = useState("");
  const [committedQ, setCommittedQ] = useState("");

  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [newSinceCount, setNewSinceCount] = useState(0);

  // Debounced search input → committed query.
  useEffect(() => {
    const t = window.setTimeout(() => setCommittedQ(searchInput.trim()), 250);
    return () => window.clearTimeout(t);
  }, [searchInput]);

  // Initial + search-change fetch (replaces visible list entirely).
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setNewSinceCount(0);
    listPosts({
      q: committedQ || undefined,
      limit: PAGE_SIZE,
      offset: 0,
    })
      .then((data) => {
        if (cancelled) return;
        setPosts(data);
        setHasMore(data.length === PAGE_SIZE);
        setError(null);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setError(e instanceof ApiError ? e : new ApiError(0, String(e)));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [committedQ]);

  // Polling — quietly merge new posts at the top.
  useEffect(() => {
    const id = window.setInterval(() => {
      if (document.visibilityState !== "visible") return;
      listPosts({
        q: committedQ || undefined,
        limit: PAGE_SIZE,
        offset: 0,
      })
        .then((data) => {
          setPosts((curr) => {
            const seen = new Set(curr.map((p) => p.id));
            const fresh = data.filter((p) => !seen.has(p.id) && p.id > 0);
            if (!fresh.length) return curr;
            setNewSinceCount((n) => n + fresh.length);
            return [...fresh, ...curr];
          });
        })
        .catch(() => {
          // swallow — polling failures shouldn't yell at the user
        });
    }, POLL_MS);
    return () => window.clearInterval(id);
  }, [committedQ]);

  const loadMore = useCallback(async () => {
    setLoadingMore(true);
    try {
      const next = await listPosts({
        q: committedQ || undefined,
        limit: PAGE_SIZE,
        offset: posts.filter((p) => p.id > 0).length,
      });
      const seen = new Set(posts.map((p) => p.id));
      const fresh = next.filter((p) => !seen.has(p.id));
      setPosts((curr) => [...curr, ...fresh]);
      if (next.length < PAGE_SIZE) setHasMore(false);
    } catch (e) {
      show(e instanceof ApiError ? e.detail : String(e), "error");
    } finally {
      setLoadingMore(false);
    }
  }, [committedQ, posts, show]);

  // Optimistic create — prepend a placeholder post, then reconcile.
  const onCompose = useCallback(
    async (message: string) => {
      if (!currentUser) throw new ApiError(401, "not signed in");
      const tempId = -Date.now();
      const optimistic: Post = {
        id: tempId,
        username: currentUser,
        message,
        created_at: new Date().toISOString().slice(0, 19),
        updated_at: null,
        board: "general",
      };
      setPosts((curr) => [optimistic, ...curr]);
      try {
        const saved = await createPost(message, currentUser);
        setPosts((curr) => curr.map((p) => (p.id === tempId ? saved : p)));
      } catch (e) {
        setPosts((curr) => curr.filter((p) => p.id !== tempId));
        throw e;
      }
    },
    [currentUser],
  );

  // Optimistic delete — remove immediately, restore if the API rejects.
  const onDelete = useCallback(
    async (post: Post) => {
      if (post.id < 0) return; // optimistic placeholder; nothing on server yet
      if (
        !window.confirm(
          `Delete this post by @${post.username}? This can't be undone.`,
        )
      )
        return;
      const idx = posts.findIndex((p) => p.id === post.id);
      setPosts((curr) => curr.filter((p) => p.id !== post.id));
      try {
        await deletePost(post.id);
        show("Post deleted.", "success");
      } catch (e) {
        // restore at original index
        setPosts((curr) => {
          const next = [...curr];
          next.splice(Math.max(0, idx), 0, post);
          return next;
        });
        show(e instanceof ApiError ? e.detail : String(e), "error");
      }
    },
    [posts, show],
  );

  return (
    <div className={styles.page}>
      <div className={styles.head}>
        <h1>Feed</h1>
        <label htmlFor={searchId} className="sr-only">
          Search posts
        </label>
        <input
          id={searchId}
          type="search"
          className={`input ${styles.search}`}
          placeholder="Search posts…"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
      </div>

      <Composer currentUser={currentUser} onSubmit={onCompose} />

      {newSinceCount > 0 && (
        <button
          type="button"
          className={styles.newBanner}
          onClick={() => {
            setNewSinceCount(0);
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
        >
          {newSinceCount} new {newSinceCount === 1 ? "post" : "posts"} — scroll
          to top
        </button>
      )}

      {error && <ErrorBanner error={error} onRetry={() => setCommittedQ((q) => q)} />}

      {loading && <LoadingDots label="Loading feed" />}

      {!loading && !error && posts.length === 0 && (
        <p className={styles.empty}>
          {committedQ
            ? `No posts match "${committedQ}".`
            : "No posts yet. Be the first."}
        </p>
      )}

      <ul className={styles.list}>
        {posts.map((p) => (
          <li key={p.id}>
            <PostCard
              post={p}
              currentUser={currentUser}
              onDelete={onDelete}
              optimistic={p.id < 0}
            />
          </li>
        ))}
      </ul>

      {!loading && !error && posts.length > 0 && (
        <LoadMore hasMore={hasMore} loading={loadingMore} onLoad={loadMore} />
      )}
    </div>
  );
}
