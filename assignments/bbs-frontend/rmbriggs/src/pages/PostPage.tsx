import { useParams, useNavigate } from "react-router-dom";
import { usePost } from "@/hooks/usePost";
import LoadingRow from "@/components/LoadingRow";
import ErrorBox from "@/components/ErrorBox";
import ThreadView from "@/components/ThreadView";

export default function PostPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { thread, loading, error, refetch, deletePost, reply } = usePost(id);

  if (error?.status === 404) return <p className="py-12 text-center text-muted-foreground">Post not found.</p>;
  if (loading) return <LoadingRow />;
  if (error) return <ErrorBox error={error} onRetry={refetch} />;
  if (!thread) return null;

  return (
    <ThreadView
      posts={thread}
      rootId={Number(id)}
      onReply={reply}
      onDelete={async (delId) => {
        await deletePost(delId);
        if (delId === Number(id)) navigate("/");
      }}
    />
  );
}
