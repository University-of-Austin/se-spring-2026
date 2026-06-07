// Mirrors A2's Pydantic response models.

export type UserOut = {
  username: string;
  created_at: string;
  bio: string;
  post_count: number;
};

export type PostOut = {
  id: number;
  username: string;
  message: string;
  created_at: string;
  updated_at: string | null;
};

export type CursorPage = {
  posts: PostOut[];
  next_cursor: string | null;
};
