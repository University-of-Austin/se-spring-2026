import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  getStoredUsername,
  setStoredUsername,
  subscribeUsername,
} from "../src/lib/storage";

afterEach(() => {
  setStoredUsername(null);
  vi.restoreAllMocks();
});

describe("storage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("round-trips a username through localStorage", () => {
    expect(getStoredUsername()).toBeNull();
    setStoredUsername("alice");
    expect(getStoredUsername()).toBe("alice");
    setStoredUsername(null);
    expect(getStoredUsername()).toBeNull();
  });

  it("dispatches an in-tab event so subscribers re-render without a refresh", () => {
    // The native `storage` event only fires for *other* tabs. The custom event
    // is what makes useCurrentUser pick up changes inside the same tab — eg
    // when the signup form sets the username and the header should update
    // immediately.
    const cb = vi.fn();
    const unsub = subscribeUsername(cb);
    setStoredUsername("alice");
    setStoredUsername("bob");
    setStoredUsername(null);
    expect(cb).toHaveBeenCalledTimes(3);
    expect(cb).toHaveBeenNthCalledWith(1, "alice");
    expect(cb).toHaveBeenNthCalledWith(2, "bob");
    expect(cb).toHaveBeenNthCalledWith(3, null);
    unsub();
    setStoredUsername("ignored");
    expect(cb).toHaveBeenCalledTimes(3);
  });

  it("tolerates a setItem throw without breaking the event channel", () => {
    // localStorage can throw in private mode or when over quota. The setter
    // catches and still fires the in-tab event so the current page stays
    // consistent.
    const spy = vi
      .spyOn(Storage.prototype, "setItem")
      .mockImplementation(() => {
        throw new DOMException("quota", "QuotaExceededError");
      });
    const cb = vi.fn();
    const unsub = subscribeUsername(cb);
    expect(() => setStoredUsername("alice")).not.toThrow();
    expect(cb).toHaveBeenCalledWith(null); // getItem still returns null since setItem threw
    spy.mockRestore();
    unsub();
  });
});
