import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getUser } from "../api/users";
import { deletePost, listUserPosts } from "../api/posts";
import { ApiError, type Post, type User } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";
import { LoadingDots } from "../components/LoadingDots";
import { PostCard } from "../components/PostCard";
import { Timestamp } from "../components/Timestamp";
import { LoadMore } from "../components/Pagination";
import { useCurrentUser } from "../hooks/useCurrentUser";
import { useToast } from "../hooks/useToast";
import styles from "./UserProfilePage.module.css";

const PAGE_SIZE = 20;

export default function UserProfilePage() {
  const { username = "" } = useParams<{ username: string }>();
  const { currentUser } = useCurrentUser();
  const { show } = useToast();

  const [user, setUser] = useState<User | null>(null);
  const [userError, setUserError] = useState<ApiError | null>(null);
  const [userLoading, setUserLoading] = useState(true);

  const [posts, setPosts] = useState<Post[]>([]);
  const [postsError, setPostsError] = useState<ApiError | null>(null);
  const [postsLoading, setPostsLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setUserLoading(true);
    setPostsLoading(true);

    getUser(username)
      .then((u) => !cancelled && setUser(u))
      .catch(
        (e: unknown) =>
          !cancelled &&
          setUserError(e instanceof ApiError ? e : new ApiError(0, String(e))),
      )
      .finally(() => !cancelled && setUserLoading(false));

    listUserPosts(username, { limit: PAGE_SIZE, offset: 0 })
      .then((data) => {
        if (cancelled) return;
        setPosts(data);
        setHasMore(data.length === PAGE_SIZE);
      })
      .catch(
        (e: unknown) =>
          !cancelled &&
          setPostsError(e instanceof ApiError ? e : new ApiError(0, String(e))),
      )
      .finally(() => !cancelled && setPostsLoading(false));

    return () => {
      cancelled = true;
    };
  }, [username]);

  const loadMore = useCallback(async () => {
    setLoadingMore(true);
    try {
      const next = await listUserPosts(username, {
        limit: PAGE_SIZE,
        offset: posts.length,
      });
      setPosts((curr) => [...curr, ...next]);
      if (next.length < PAGE_SIZE) setHasMore(false);
    } catch (e) {
      show(e instanceof ApiError ? e.detail : String(e), "error");
    } finally {
      setLoadingMore(false);
    }
  }, [username, posts.length, show]);

  const onDelete = useCallback(
    async (post: Post) => {
      if (!window.confirm(`Delete this post? This can't be undone.`)) return;
      const idx = posts.findIndex((p) => p.id === post.id);
      setPosts((curr) => curr.filter((p) => p.id !== post.id));
      try {
        await deletePost(post.id);
        show("Post deleted.", "success");
      } catch (e) {
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

  if (userLoading) return <LoadingDots label="Loading profile" />;

  if (userError && userError.status === 404) {
    return (
      <div className={styles.notFound}>
        <h1>User not found</h1>
        <p className="muted">
          There's no user named <code>@{username}</code>.
        </p>
        <Link to="/users" className="btn">
          ← All users
        </Link>
      </div>
    );
  }

  if (userError) return <ErrorBanner error={userError} />;
  if (!user) return null;

  return (
    <div className={styles.page}>
      <section className={styles.card}>
        <div className={styles.identity}>
          <div className={styles.avatar} aria-hidden="true">
            {user.username[0]?.toUpperCase() ?? "?"}
          </div>
          <div>
            <h1 className={styles.name}>@{user.username}</h1>
            <p className="subtle">
              Member since <Timestamp value={user.created_at} /> ·{" "}
              {user.post_count} {user.post_count === 1 ? "post" : "posts"}
            </p>
            {user.bio && <p className={styles.bio}>{user.bio}</p>}
          </div>
        </div>
      </section>

      <h2 className={styles.postsHeading}>Posts</h2>

      {postsError && <ErrorBanner error={postsError} />}
      {postsLoading && !posts.length && <LoadingDots label="Loading posts" />}

      {!postsLoading && !postsError && posts.length === 0 && (
        <p className="muted">No posts yet.</p>
      )}

      <ul className={styles.list}>
        {posts.map((p) => (
          <li key={p.id}>
            <PostCard
              post={p}
              currentUser={currentUser}
              onDelete={onDelete}
            />
          </li>
        ))}
      </ul>

      {!postsLoading && !postsError && posts.length > 0 && (
        <LoadMore hasMore={hasMore} loading={loadingMore} onLoad={loadMore} />
      )}
    </div>
  );
}
