// The showpiece test for the stale-fetch bug agents skip.
//
// Scenario: deps change from "A" to "B".  The fetch for "A" is slow;
// the fetch for "B" is fast.  When the slow "A" eventually resolves,
// it must NOT overwrite the newer "B" state.

import { describe, it, expect } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useState } from "react";
import { useApi } from "./useApi";

describe("useApi", () => {
  it("ignores a stale fetch result after deps change", async () => {
    // Deferred promises let us control resolution order from the test.
    let resolveA: (v: string) => void = () => {};
    let resolveB: (v: string) => void = () => {};
    const promiseA = new Promise<string>((r) => { resolveA = r; });
    const promiseB = new Promise<string>((r) => { resolveB = r; });

    function useTest(key: "A" | "B") {
      return useApi(
        () => (key === "A" ? promiseA : promiseB),
        [key],
      );
    }

    const { result, rerender } = renderHook(
      ({ key }: { key: "A" | "B" }) => useTest(key),
      { initialProps: { key: "A" as "A" | "B" } },
    );

    // Switch deps before A resolves.
    rerender({ key: "B" });

    // Resolve B first.
    await act(async () => {
      resolveB("B-value");
      await Promise.resolve();
    });

    // State should reflect B.
    await waitFor(() => {
      expect(result.current.data).toBe("B-value");
    });

    // Now resolve A.  This must NOT overwrite B.
    await act(async () => {
      resolveA("A-value");
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(result.current.data).toBe("B-value");
  });

  it("starts with loading=true and transitions to data on resolve", async () => {
    const { result } = renderHook(() =>
      useApi(() => Promise.resolve(123), []),
    );

    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
      expect(result.current.data).toBe(123);
    });
  });

  it("refetch() retriggers the fetcher", async () => {
    let callCount = 0;
    const { result } = renderHook(() =>
      useApi(() => {
        callCount++;
        return Promise.resolve(callCount);
      }, []),
    );

    await waitFor(() => expect(result.current.data).toBe(1));

    act(() => {
      result.current.refetch();
    });

    await waitFor(() => expect(result.current.data).toBe(2));
  });

  // Verify the hook can be embedded inside a component that owns
  // its own state (sanity check that React state and hook deps
  // compose normally — uses a real component pattern).
  it("works when consumed from a component with local state", async () => {
    function Wrapper() {
      const [key] = useState("only");
      return useApi(() => Promise.resolve(key), [key]);
    }

    const { result } = renderHook(() => Wrapper());
    await waitFor(() => expect(result.current.data).toBe("only"));
  });
});
