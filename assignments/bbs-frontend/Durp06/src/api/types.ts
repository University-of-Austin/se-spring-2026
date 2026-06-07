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
  updated_at: string;
}

export interface PostsPage {
  posts: Post[];
  nextCursor: string | null;
}
