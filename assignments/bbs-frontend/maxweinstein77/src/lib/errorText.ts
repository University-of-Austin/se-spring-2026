// Pull a user-facing string out of an unknown error value. ApiError and
// plain Error both have a useful .message; anything else falls back to a
// generic label so we never render "[object Object]" at the user.

export function errorText(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}
