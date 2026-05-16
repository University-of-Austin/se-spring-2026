// API response types from the A2 backend.

export interface User {
  username: string;
  created_at: string;
  bio: string | null;
  post_count: number;
}

export interface Post {
  id: number;
  username: string;
  board: string;
  message: string;
  created_at: string;
  updated_at: string | null;
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
