// Single post view. Reuses PostRow with the delete button enabled.
// On successful delete, navigate back to the feed.

import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../../api/client";
import { ErrorMessage } from "../../components/ErrorMessage";
import { Loading } from "../../components/Loading";
import { PostRow } from "../../components/PostRow";
import { useDeletePost, usePost } from "../../hooks/usePosts";
import { errorText } from "../../lib/errorText";
import styles from "./PostDetail.module.css";

export function PostDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const postId = id !== undefined ? Number(id) : undefined;
  const isInvalidId = postId === undefined || Number.isNaN(postId);

  const post = usePost(postId);
  const deletePost = useDeletePost();

  if (isInvalidId) {
    return <p className={styles.notFound}>Invalid post id.</p>;
  }
  if (post.isLoading) return <Loading label="Loading post..." />;

  // Treat 404 as a friendly "not found" view rather than a red error banner.
  if (post.isError) {
    const status = post.error instanceof ApiError ? post.error.status : null;
    if (status === 404) {
      return (
        <div className={styles.notFound}>
          <h1>Post not found</h1>
          <p>It may have been deleted.</p>
          <Link to="/">Back to feed</Link>
        </div>
      );
    }
    return (
      <ErrorMessage
        message={errorText(post.error, "Failed to load post.")}
        onRetry={() => post.refetch()}
      />
    );
  }

  if (!post.data) return null;

  async function handleDelete(targetId: number) {
    try {
      await deletePost.mutateAsync(targetId);
      navigate("/");
    } catch {
      // useDeletePost.onError already rolled back the cache; we don't need
      // to do anything here -- the PostRow will re-render with the snapshot.
    }
  }

  return (
    <section className={styles.wrap}>
      <Link to="/" className={styles.back}>← Back to feed</Link>
      <PostRow
        post={post.data}
        onDelete={handleDelete}
        deleting={deletePost.isPending}
      />
    </section>
  );
}
