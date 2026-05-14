import "@testing-library/jest-dom/vitest";

// Node 25 ships a native localStorage stub that masks jsdom's implementation.
// The native version has no working methods unless --localstorage-file is set.
// Since the global descriptor is configurable, we replace it with jsdom's.
declare const jsdom: { window: Window & typeof globalThis };
if (typeof jsdom !== "undefined" && jsdom.window?.localStorage) {
  const jsdomStorage = jsdom.window.localStorage;
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    get: () => jsdomStorage,
  });
}

// jsdom does not implement EventSource. Provide a no-op stub so tests that
// don't exercise SSE behaviour don't throw "EventSource is not defined".
// Individual tests override this with vi.stubGlobal("EventSource", FakeES).
if (typeof globalThis.EventSource === "undefined") {
  class NoopEventSource {
    onmessage: ((e: MessageEvent) => void) | null = null;
    onerror: ((e: Event) => void) | null = null;
    constructor(public url: string) {}
    close() {}
  }
  Object.defineProperty(globalThis, "EventSource", {
    configurable: true,
    writable: true,
    value: NoopEventSource,
  });
}
