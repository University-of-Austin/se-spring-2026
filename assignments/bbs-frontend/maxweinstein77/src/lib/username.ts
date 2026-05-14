// localStorage helpers for the current "Acting as" username.
// X-Username isn't real auth -- this is a profile selector that survives refresh.

const KEY = "bbs.username";

export function getStoredUsername(): string | null {
  return localStorage.getItem(KEY);
}

export function setStoredUsername(username: string): void {
  localStorage.setItem(KEY, username);
}

export function clearStoredUsername(): void {
  localStorage.removeItem(KEY);
}
