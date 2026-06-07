export interface User {
  username: string;
  created_at: string;
  bio: string;
  post_count: number;
}

export interface Post {
  id: number;
  username: string;
  message: string;
  created_at: string;
  updated_at: string | null;
  reactions: Record<string, number>;
}

export interface PostsQuery {
  q?: string;
  username?: string;
  limit?: number;
  offset?: number;
}

export const USERNAME_REGEX = /^[a-zA-Z0-9_]+$/;
export const USERNAME_MIN = 3;
export const USERNAME_MAX = 20;
export const MESSAGE_MIN = 1;
export const MESSAGE_MAX = 500;
