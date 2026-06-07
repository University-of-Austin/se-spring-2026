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
  board: string;
};

export type Reaction = {
  post_id: number;
  username: string;
  kind: string;
};

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}
