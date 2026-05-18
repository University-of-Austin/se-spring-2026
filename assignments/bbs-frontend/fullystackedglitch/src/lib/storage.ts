const KEY = "bbs:username";
const EVENT = "bbs:username-changed";

export function getStoredUsername(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setStoredUsername(name: string | null) {
  try {
    if (name === null) localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, name);
  } catch {
    // Storage may throw in private mode or with quota exceeded; the app still
    // works for the current tab via the event channel below.
  }
  window.dispatchEvent(new CustomEvent(EVENT, { detail: name }));
}

export function subscribeUsername(cb: (name: string | null) => void): () => void {
  const handler = () => cb(getStoredUsername());
  window.addEventListener(EVENT, handler);
  window.addEventListener("storage", handler);
  return () => {
    window.removeEventListener(EVENT, handler);
    window.removeEventListener("storage", handler);
  };
}
