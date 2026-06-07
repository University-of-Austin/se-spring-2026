// API response types from the A2 backend.

export interface User {
  username: string;
  created_at: string;
  bio: string | null;
  post_count: number;
  avatar_url: string | null;
}

export interface Post {
  id: number;
  username: string;
  board: string;
  message: string;
  created_at: string;
  updated_at: string | null;
  avatar_url: string | null;
  image_url: string | null;
}

export interface DMMessage {
  id: number;
  from_username: string;
  to_username: string;
  from_me: boolean;
  message: string;
  created_at: string;
  read_at: string | null;
}

export interface DMConversation {
  partner: { username: string; avatar_url: string | null };
  last_message: {
    message: string;
    created_at: string;
    from_me: boolean;
    read_at: string | null;
  };
  unread_count: number;
}

export interface DMThread {
  partner: { username: string; avatar_url: string | null };
  messages: DMMessage[];
}

export interface LoginResponse {
  token: string;
  username: string;
}

export interface Board {
  name: string;
  created_at: string;
  post_count: number;
}

// A 422 from FastAPI looks like {"detail": [...]} (Pydantic validation errors)
// or {"detail": "string message"} for HTTPException. We normalize to a string.
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}
