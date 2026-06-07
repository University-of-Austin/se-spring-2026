import { describe, expect, test } from 'vitest';
import {
  POST_MAX,
  USERNAME_MAX,
  USERNAME_MIN,
  isPostSubmittable,
  isUsernameSubmittable,
  validatePost,
  validateUsername,
} from '../../src/lib/validate';

describe('validateUsername', () => {
  test('rejects too-short usernames', () => {
    expect(validateUsername('ab')).toMatch(/at least/i);
    expect(validateUsername('a')).toMatch(/at least/i);
  });

  test('rejects too-long usernames', () => {
    const tooLong = 'a'.repeat(USERNAME_MAX + 1);
    expect(validateUsername(tooLong)).toMatch(/at most/i);
  });

  test('rejects invalid characters', () => {
    expect(validateUsername('alice-1')).toMatch(/letters, numbers, and underscore/i);
    expect(validateUsername('hi there')).toMatch(/letters, numbers, and underscore/i);
    expect(validateUsername('café')).toMatch(/letters, numbers, and underscore/i);
  });

  test('accepts valid usernames at length boundaries', () => {
    expect(validateUsername('a'.repeat(USERNAME_MIN))).toBeNull();
    expect(validateUsername('a'.repeat(USERNAME_MAX))).toBeNull();
    expect(validateUsername('alice_42')).toBeNull();
  });

  test('isUsernameSubmittable matches validateUsername', () => {
    expect(isUsernameSubmittable('alice')).toBe(true);
    expect(isUsernameSubmittable('ab')).toBe(false);
    expect(isUsernameSubmittable('')).toBe(false);
  });
});

describe('validatePost', () => {
  test('empty is "incomplete" not error', () => {
    expect(validatePost('')).toBeNull();
  });

  test('rejects over-limit messages', () => {
    expect(validatePost('x'.repeat(POST_MAX + 1))).toMatch(/at most/i);
  });

  test('accepts at-limit messages', () => {
    expect(validatePost('x'.repeat(POST_MAX))).toBeNull();
  });

  test('isPostSubmittable requires non-whitespace content', () => {
    expect(isPostSubmittable('')).toBe(false);
    expect(isPostSubmittable('   ')).toBe(false);
    expect(isPostSubmittable('hi')).toBe(true);
    expect(isPostSubmittable('x'.repeat(POST_MAX + 1))).toBe(false);
  });
});
