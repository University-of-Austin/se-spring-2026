// Wire types — the JSON shapes A2 actually sends.
// Kept in sync by hand with the Pydantic models in
// assignments/bbs-webserver/Emessjay/webserver/main.py.

export type UserOut = {
  username: string;
  bio: string | null;
  created_at: string;   // ISO-8601 UTC string
  post_count: number;
};

export type PostOut = {
  id: number;
  username: string;
  message: string;
  board: string | null;
  created_at: string;
  updated_at: string | null;
};
