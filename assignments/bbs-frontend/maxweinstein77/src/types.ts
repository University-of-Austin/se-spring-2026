// Shapes returned by the A2 BBS API. Annotate at boundaries (per lecture 5.1).

export interface User {
  username: string;
  created_at: string;
  bio: string | null;
  post_count: number;
}

export interface Post {
  id: number;
  username: string;
  message: string;
  created_at: string;
  updated_at: string | null;
}

export interface Reaction {
  post_id: number;
  username: string;
  kind: string;
}
