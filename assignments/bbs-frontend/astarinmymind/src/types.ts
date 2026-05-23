// Shapes returned by the A2 BBS API.
// If your backend response keys ever change, update them here once and
// every consumer (hooks, components) gets the new types automatically.

export type User = {
  username: string
  bio: string | null
  created_at: string
  post_count: number
}

export type Post = {
  id: number
  username: string
  message: string
  created_at: string
  updated_at: string | null
}
