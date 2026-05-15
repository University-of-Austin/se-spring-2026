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
  updated_at: string | null;
};

export type PostsQuery = {
  q?: string;
  username?: string;
  limit?: number;
  offset?: number;
};

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail || `HTTP ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}
