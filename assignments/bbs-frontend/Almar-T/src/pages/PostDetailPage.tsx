import { Link, useNavigate, useParams } from "react-router-dom";
import { deletePost, getPost } from "../api/posts";
import { ApiError } from "../api/types";
import { useFetch } from "../hooks/useFetch";
import { ErrorBanner } from "../components/ErrorBanner";
import { LoadingDots } from "../components/LoadingDots";
import { PostCard } from "../components/PostCard";
import { useCurrentUser } from "../hooks/useCurrentUser";
import { useToast } from "../hooks/useToast";
import styles from "./PostDetailPage.module.css";

export default function PostDetailPage() {
  const { id = "" } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentUser } = useCurrentUser();
  const { show } = useToast();

  const { data: post, error, loading, refetch } = useFetch(
    () => getPost(id),
    [id],
  );

  const onDelete = async () => {
    if (!post) return;
    if (!window.confirm("Delete this post? This can't be undone.")) return;
    try {
      await deletePost(post.id);
      show("Post deleted.", "success");
      navigate("/");
    } catch (e) {
      show(e instanceof ApiError ? e.detail : String(e), "error");
    }
  };

  if (loading) return <LoadingDots label="Loading post" />;

  if (error && error.status === 404) {
    return (
      <div className={styles.notFound}>
        <h1>Post not found</h1>
        <p className="muted">
          Post <code>#{id}</code> doesn't exist. It may have been deleted.
        </p>
        <Link to="/" className="btn">
          ← Back to feed
        </Link>
      </div>
    );
  }

  if (error) return <ErrorBanner error={error} onRetry={refetch} />;
  if (!post) return null;

  return (
    <div className={styles.page}>
      <Link to="/" className={styles.back}>
        ← Feed
      </Link>
      <PostCard
        post={post}
        currentUser={currentUser}
        onDelete={onDelete}
      />
    </div>
  );
}
