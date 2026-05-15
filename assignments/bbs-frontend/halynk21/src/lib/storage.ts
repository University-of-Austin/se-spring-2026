// Typed wrappers around localStorage. All ops swallow errors so a private-
// browsing window (which can throw on access, not just write) doesn't crash
// the app — values just don't persist. Cross-tab sync lives in UserContext,
// not here, since storage events need React lifecycle.

const PREFIX = 'bbs:';

function key(name: string): string {
  return PREFIX + name;
}

export function get(name: string): string | null {
  try {
    return localStorage.getItem(key(name));
  } catch {
    return null;
  }
}

export function set(name: string, value: string): void {
  try {
    localStorage.setItem(key(name), value);
  } catch {
    /* private browsing or quota — silently drop */
  }
}

export function remove(name: string): void {
  try {
    localStorage.removeItem(key(name));
  } catch {
    /* same */
  }
}

// The full prefixed key — used by code that listens for `storage` events.
export function fullKey(name: string): string {
  return key(name);
}
