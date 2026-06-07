// Mirrors the A2 server's validation: usernames 3-20 chars matching
// ^[a-zA-Z0-9_]+$, posts 1-500 chars. Frontend validates to keep the
// submit button honest; the server is still the source of truth (we
// surface 422s via ApiError.fieldErrors).

export const USERNAME_REGEX = /^[a-zA-Z0-9_]+$/;
export const USERNAME_MIN = 3;
export const USERNAME_MAX = 20;

export const POST_MIN = 1;
export const POST_MAX = 500;

export function validateUsername(s: string): string | null {
  if (s.length === 0) return 'Username is required';
  if (s.length < USERNAME_MIN) return `At least ${USERNAME_MIN} characters`;
  if (s.length > USERNAME_MAX) return `At most ${USERNAME_MAX} characters`;
  if (!USERNAME_REGEX.test(s)) return 'Letters, numbers, and underscore only';
  return null;
}

export function validatePost(s: string): string | null {
  // Empty is "incomplete," not error — submit button is just disabled.
  if (s.length === 0) return null;
  if (s.length > POST_MAX) return `At most ${POST_MAX} characters`;
  return null;
}

export function isPostSubmittable(s: string): boolean {
  const t = s.trim();
  return t.length >= POST_MIN && s.length <= POST_MAX;
}

export function isUsernameSubmittable(s: string): boolean {
  return validateUsername(s) === null;
}
