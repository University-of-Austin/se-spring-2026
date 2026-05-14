import type { ApiError } from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

const readUsername = (): string | null => {
  try {
    return localStorage.getItem("username");
  } catch {
    return null;
  }
};

export async function apiFetch<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  const username = readUsername();
  if (username) headers["X-Username"] = username;
  if (init.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";

  const res = await fetch(`${BASE}${path}`, { ...init, headers });

  if (res.status === 204) return null as T;

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;

  if (!res.ok) {
    const err: ApiError = { status: res.status, detail: data?.detail ?? res.statusText };
    throw err;
  }

  return data as T;
}
