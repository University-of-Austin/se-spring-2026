// Single user profile: their info + every post they've written.
// 404 view if the user doesn't exist (per spec).

import { Link, useParams } from "react-router-dom";
import { ApiError } from "../../api/client";
import { ErrorMessage } from "../../components/ErrorMessage";
import { Loading } from "../../components/Loading";
import { PostRow } from "../../components/PostRow";
import { useDeletePost, useUserPosts } from "../../hooks/usePosts";
import { useUser } from "../../hooks/useUsers";
import { errorText } from "../../lib/errorText";
import styles from "./UserProfile.module.css";

export function UserProfile() {
  const { username } = useParams<{ username: string }>();
  const user = useUser(username);
  const posts = useUserPosts(username);
  const deletePost = useDeletePost();

  if (user.isLoading) return <Loading label="Loading profile..." />;

  if (user.isError) {
    const status = user.error instanceof ApiError ? user.error.status : null;
    if (status === 404) {
      return (
        <div className={styles.notFound}>
          <h1>User not found</h1>
          <p>No user named "{username}" exists.</p>
          <Link to="/users">See all users</Link>
        </div>
      );
    }
    return (
      <ErrorMessage
        message={errorText(user.error, "Failed to load user.")}
        onRetry={() => user.refetch()}
      />
    );
  }

  if (!user.data) return null;

  return (
    <section>
      <header className={styles.header}>
        <h1 className={styles.name}>{user.data.username}</h1>
        {user.data.bio && <p className={styles.bio}>{user.data.bio}</p>}
        <p className={styles.meta}>
          {user.data.post_count} {user.data.post_count === 1 ? "post" : "posts"} ·
          joined {new Date(user.data.created_at).toLocaleDateString()}
        </p>
      </header>

      <h2 className={styles.postsHeading}>Posts</h2>

      {posts.isLoading && <Loading label="Loading posts..." />}

      {posts.isError && (
        <ErrorMessage
          message={errorText(posts.error, "Failed to load posts.")}
          onRetry={() => posts.refetch()}
        />
      )}

      {posts.isSuccess && (posts.data?.length ?? 0) === 0 && (
        <p className={styles.empty}>{user.data.username} hasn't posted yet.</p>
      )}

      {posts.data && posts.data.length > 0 && (
        <ul className={styles.list}>
          {posts.data.map((post) => (
            <li key={post.id}>
              <PostRow
                post={post}
                onDelete={(id) => deletePost.mutate(id)}
                deleting={deletePost.isPending && deletePost.variables === post.id}
              />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
