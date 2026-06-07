export type User = {
  username: string;
  created_at: string;
  bio: string;
  post_count: number;
};

export type Post = {
  id: number;
  username: string;
  message: string;
  created_at: string;
  updated_at?: string | null;
};

export type PostListQuery = {
  q?: string;
  username?: string;
  limit?: number;
  offset?: number;
};
