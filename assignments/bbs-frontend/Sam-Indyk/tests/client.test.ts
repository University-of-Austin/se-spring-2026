import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "../src/api/client";

const originalFetch = globalThis.fetch;

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

describe("api client", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("listPosts() builds the query string from PostsQuery", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => jsonResponse([]));
    globalThis.fetch = fetchMock;

    await api.listPosts({ q: "hi", username: "alice", limit: 5, offset: 10 });

    expect(fetchMock).toHaveBeenCalledOnce();
    const url = String(fetchMock.mock.calls[0][0]);
    // Order of params is deterministic per URLSearchParams.
    expect(url).toContain("?q=hi");
    expect(url).toContain("username=alice");
    expect(url).toContain("limit=5");
    expect(url).toContain("offset=10");
  });

  it("createPost() sends body and X-Username header", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      jsonResponse(
        {
          id: 1,
          username: "alice",
          message: "hi",
          created_at: "2026-05-13T00:00:00",
          updated_at: null,
          reactions: {},
        },
        { status: 201 }
      )
    );
    globalThis.fetch = fetchMock;

    const post = await api.createPost("hi", "alice");

    expect(post.username).toBe("alice");
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual({ message: "hi" });
    const headers = init.headers as Record<string, string>;
    expect(headers["X-Username"]).toBe("alice");
    expect(headers["Content-Type"]).toBe("application/json");
  });

  it("throws ApiError with the detail string on 4xx", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      jsonResponse({ detail: "user not found" }, { status: 404, statusText: "Not Found" })
    );
    globalThis.fetch = fetchMock;

    await expect(api.getUser("ghost")).rejects.toThrow(ApiError);
    try {
      await api.getUser("ghost");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).status).toBe(404);
      expect((e as ApiError).message).toBe("user not found");
    }
  });

  it("surfaces FastAPI 422 validation-error array as a joined string", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      jsonResponse(
        {
          detail: [
            { loc: ["body", "message"], msg: "String should have at most 500 characters", type: "string_too_long" },
            { loc: ["body", "message"], msg: "field required", type: "missing" },
          ],
        },
        { status: 422 }
      )
    );
    globalThis.fetch = fetchMock;

    try {
      await api.createPost("x", "alice");
      throw new Error("should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      const err = e as ApiError;
      expect(err.status).toBe(422);
      expect(err.message).toContain("at most 500 characters");
      expect(err.message).toContain("field required");
    }
  });

  it("returns undefined on 204 No Content (deletePost)", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => new Response(null, { status: 204 }));
    globalThis.fetch = fetchMock;

    const result = await api.deletePost(7);
    expect(result).toBeUndefined();
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("DELETE");
  });

  it("wraps network-level failures as ApiError with status 0", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () => {
      throw new TypeError("fetch failed");
    });
    globalThis.fetch = fetchMock;

    try {
      await api.listUsers();
      throw new Error("should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).status).toBe(0);
      expect((e as ApiError).message).toContain("Could not reach the server");
    }
  });
});
