import { ApiError } from "./types";

export const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined) ??
  "http://localhost:8000";

type Json = Record<string, unknown> | unknown[] | string | number | boolean | null;

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError(
      0,
      `Could not reach the backend at ${API_BASE}. Is uvicorn running?`,
    );
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  let body: Json = null;
  if (text) {
    try {
      body = JSON.parse(text) as Json;
    } catch {
      body = text;
    }
  }

  if (!res.ok) {
    throw new ApiError(res.status, extractDetail(body, res));
  }
  return body as T;
}

function extractDetail(body: Json, res: Response): string {
  if (body && typeof body === "object" && !Array.isArray(body)) {
    const d = (body as { detail?: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) {
      // FastAPI 422 shape: [{ loc, msg, type }, ...]
      const msgs = d
        .map((entry) => {
          if (entry && typeof entry === "object") {
            const m = (entry as { msg?: unknown }).msg;
            if (typeof m === "string") return m;
          }
          return null;
        })
        .filter(Boolean);
      if (msgs.length) return msgs.join("; ");
    }
  }
  return `${res.status} ${res.statusText || "request failed"}`;
}
