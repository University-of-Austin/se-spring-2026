import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useApi } from "../src/hooks/useApi";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useApi", () => {
  it("starts loading, resolves with data, clears loading", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce({ value: 42 });
    const { result } = renderHook(() => useApi(fetcher, "k1"));

    // Loading is true synchronously, before the promise resolves. This is the
    // contract: views can render the loading branch immediately on mount,
    // never a blank data.map(...).
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeUndefined();
    expect(result.current.error).toBeNull();

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual({ value: 42 });
    expect(result.current.error).toBeNull();
  });

  it("surfaces a rejected promise as error and clears loading", async () => {
    const fetcher = vi.fn().mockRejectedValueOnce(new Error("nope"));
    const { result } = renderHook(() => useApi(fetcher, "k2"));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe("nope");
    expect(result.current.data).toBeUndefined();
  });

  it("refetch re-runs the fetcher and toggles loading", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce("first")
      .mockResolvedValueOnce("second");
    const { result } = renderHook(() => useApi(fetcher, "k3"));

    await waitFor(() => expect(result.current.data).toBe("first"));
    expect(fetcher).toHaveBeenCalledTimes(1);

    act(() => result.current.refetch());
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.data).toBe("second"));
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("aborts the in-flight fetch when the key changes", async () => {
    // The signal received by fetcher #1 must become aborted when key changes,
    // so cancellable fetches (real ones) don't waste resources after the user
    // navigates or paginates away from a stale request.
    let firstSignal: AbortSignal | undefined;
    const fetcher = vi.fn((signal: AbortSignal) => {
      if (!firstSignal) firstSignal = signal;
      return new Promise<string>(() => {
        // Never resolves — we just want to check the signal flips on abort.
      });
    });

    const { rerender } = renderHook(({ k }) => useApi(fetcher, k), {
      initialProps: { k: "first" },
    });

    expect(firstSignal?.aborted).toBe(false);
    rerender({ k: "second" });
    expect(firstSignal?.aborted).toBe(true);
  });
});
