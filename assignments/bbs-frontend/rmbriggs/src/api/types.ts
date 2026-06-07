export type User = {
  username: string;
  created_at: string;
  bio: string | null;
  post_count: number;
};

export type Post = {
  id: number;
  username: string;
  message: string;
  created_at: string;
  updated_at: string | null;
  board: string | null;
  parent_id: number | null;
  reaction_counts: Record<string, number>;
};

export type Board = {
  name: string;
  description: string | null;
  created_at: string;
  post_count: number;
};

export type FeedPage = { posts: Post[]; next_cursor: string | null; has_more: boolean };

export type ApiError = { status: number; detail: string | Array<{ msg: string; loc: unknown[]; type: string }> };

export const isApiError = (e: unknown): e is ApiError =>
  typeof e === "object" && e !== null && "status" in e && "detail" in e;

export const formatDetail = (detail: ApiError["detail"]): string =>
  typeof detail === "string" ? detail : detail.map((d) => d.msg).join("; ");
