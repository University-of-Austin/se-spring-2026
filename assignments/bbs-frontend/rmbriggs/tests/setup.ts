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
