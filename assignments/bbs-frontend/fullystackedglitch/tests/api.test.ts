import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "../src/lib/api";

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

function mockResponse(status: number, body: unknown): Response {
  const text = body === undefined ? "" : JSON.stringify(body);
  return new Response(text, {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("api wrapper", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  it("returns parsed JSON on success", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      mockResponse(200, [{ id: 1, username: "alice", message: "hi", created_at: "t" }]),
    );
    const posts = await api.listPosts();
    expect(posts).toHaveLength(1);
    expect(posts[0].username).toBe("alice");
  });

  it("surfaces FastAPI 422 detail as ApiError.message", async () => {
    // FastAPI emits this shape for Pydantic validation failures. The wrapper
    // pulls the first `msg` into the human-readable error so views don't
    // have to re-parse.
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      mockResponse(422, {
        detail: [
          {
            loc: ["body", "message"],
            msg: "String should have at most 500 characters",
            type: "value_error",
          },
        ],
      }),
    );
    await expect(api.createPost("x".repeat(600), "alice")).rejects.toMatchObject({
      status: 422,
      message: "String should have at most 500 characters",
    });
  });

  it("sends X-Username header on writes", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      mockResponse(201, {
        id: 7,
        username: "alice",
        message: "hi",
        created_at: "t",
      }),
    );
    globalThis.fetch = fetchMock;

    await api.createPost("hi", "alice");

    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(init.headers["X-Username"]).toBe("alice");
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(init.body)).toEqual({ message: "hi" });
  });

  it("throws ApiError instance with correct status on 404", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      mockResponse(404, { detail: "User not found" }),
    );
    try {
      await api.getUser("ghost");
      expect.fail("expected throw");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).status).toBe(404);
      expect((e as ApiError).message).toBe("User not found");
    }
  });

  it("wraps non-JSON success body as ApiError (third-failure-mode)", async () => {
    // A 2xx with an HTML body is what you get when a proxy / load balancer
    // intercepts the request. The raw SyntaxError from JSON.parse isn't
    // useful — the wrapper should surface a structured ApiError instead.
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response("<html>bad gateway</html>", {
        status: 200,
        headers: { "Content-Type": "text/html" },
      }),
    );
    await expect(api.listUsers()).rejects.toMatchObject({
      status: 200,
      message: expect.stringContaining("non-JSON"),
    });
  });

  it("returns undefined for 204 No Content (delete)", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(null, { status: 204 }),
    );
    await expect(api.deletePost(1)).resolves.toBeUndefined();
  });
});
