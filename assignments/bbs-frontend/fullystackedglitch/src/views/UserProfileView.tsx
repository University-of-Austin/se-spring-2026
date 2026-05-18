import { useCallback, useEffect, useId, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { PostRow } from "../components/PostRow";
import {
  EmptyBlock,
  ErrorBlock,
  LoadingBlock,
} from "../components/StatusBlock";
import { useApi } from "../hooks/useApi";
import { useCurrentUser } from "../hooks/useCurrentUser";
import { ApiError, api } from "../lib/api";
import type { Post, User } from "../lib/types";
import styles from "./UserProfileView.module.css";

export function UserProfileView() {
  const { username = "" } = useParams<{ username: string }>();
  const me = useCurrentUser();
  const isMe = me === username;

  const userFetcher = useCallback(
    (signal: AbortSignal) => api.getUser(username, signal),
    [username],
  );
  const postsFetcher = useCallback(
    (signal: AbortSignal) => api.getUserPosts(username, signal),
    [username],
  );

  const user = useApi(userFetcher, `user:${username}`);
  const posts = useApi(postsFetcher, `user-posts:${username}`);

  // 404 surfaces here — the api wrapper throws ApiError with status 404.
  if (user.error instanceof ApiError && user.error.status === 404) {
    return (
      <section className={styles.notFound}>
        <h1>user not found</h1>
        <p>no user named @{username}.</p>
        <Link to="/users">back to users</Link>
      </section>
    );
  }

  return (
    <section>
      {user.loading && <LoadingBlock label="Loading profile" />}
      {user.error && !(user.error instanceof ApiError && user.error.status === 404) && (
        <ErrorBlock error={user.error} onRetry={user.refetch} />
      )}
      {user.data && (
        <ProfileHeader user={user.data} isMe={isMe} onSaved={user.refetch} />
      )}

      <h2>posts</h2>
      {posts.loading && <LoadingBlock label="Loading posts" />}
      {posts.error && <ErrorBlock error={posts.error} onRetry={posts.refetch} />}
      {posts.data && posts.data.length === 0 && (
        <EmptyBlock>no posts yet.</EmptyBlock>
      )}
      <PostList posts={posts.data ?? []} onChanged={posts.refetch} />
    </section>
  );
}

function PostList({
  posts,
  onChanged,
}: {
  posts: Post[];
  onChanged: () => void;
}) {
  const [localPosts, setLocalPosts] = useState<Post[]>(posts);
  const [deletingIds, setDeletingIds] = useState<Set<number>>(new Set());

  useEffect(() => setLocalPosts(posts), [posts]);

  const onDelete = async (post: Post) => {
    if (deletingIds.has(post.id)) return;
    const snapshot = localPosts;
    setLocalPosts((prev) => prev.filter((p) => p.id !== post.id));
    setDeletingIds((prev) => new Set(prev).add(post.id));
    try {
      await api.deletePost(post.id);
      onChanged();
    } catch {
      setLocalPosts(snapshot);
    } finally {
      setDeletingIds((prev) => {
        const next = new Set(prev);
        next.delete(post.id);
        return next;
      });
    }
  };

  return (
    <div className={styles.list}>
      {localPosts.map((p) => (
        <PostRow
          key={p.id}
          post={p}
          onDelete={onDelete}
          deleting={deletingIds.has(p.id)}
          showAuthor={false}
        />
      ))}
    </div>
  );
}

function ProfileHeader({
  user,
  isMe,
  onSaved,
}: {
  user: User;
  isMe: boolean;
  onSaved: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [bio, setBio] = useState(user.bio);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bioId = useId();
  const me = useCurrentUser();

  useEffect(() => setBio(user.bio), [user.bio]);

  const save = async () => {
    if (!me) return;
    setSaving(true);
    setError(null);
    try {
      await api.patchUserBio(user.username, bio, me);
      setEditing(false);
      onSaved();
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : (e as Error).message ?? "save failed",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <header className={styles.header}>
      <div className={styles.headerTop}>
        <span className={styles.handle}>@{user.username}</span>
        <span className={styles.meta}>
          {user.post_count} post{user.post_count === 1 ? "" : "s"} · joined{" "}
          {new Date(user.created_at).toLocaleDateString()}
        </span>
      </div>
      {editing ? (
        <div className={styles.bioForm}>
          <label htmlFor={bioId} className="sr-only">
            Bio
          </label>
          <textarea
            id={bioId}
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            maxLength={200}
            placeholder="tell people about yourself…"
          />
          {error && (
            <span role="alert" style={{ color: "var(--danger)", fontSize: 13 }}>
              {error}
            </span>
          )}
          <div className={styles.bioActions}>
            <button
              type="button"
              className={styles.btnPrimary}
              onClick={save}
              disabled={saving}
            >
              {saving ? "saving…" : "save"}
            </button>
            <button
              type="button"
              className={styles.btnGhost}
              onClick={() => {
                setEditing(false);
                setBio(user.bio);
                setError(null);
              }}
              disabled={saving}
            >
              cancel
            </button>
            <span className={styles.meta}>{bio.length}/200</span>
          </div>
        </div>
      ) : (
        <div className={styles.bioForm}>
          {user.bio ? (
            <span className={styles.bio}>{user.bio}</span>
          ) : (
            <span className={`${styles.bio} ${styles.bioEmpty}`}>no bio yet.</span>
          )}
          {isMe && (
            <div className={styles.bioActions}>
              <button
                type="button"
                className={styles.btnGhost}
                onClick={() => setEditing(true)}
              >
                edit bio
              </button>
            </div>
          )}
        </div>
      )}
    </header>
  );
}
