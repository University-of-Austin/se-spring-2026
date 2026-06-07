import { act, renderHook } from '@testing-library/react';
import { describe, expect, test } from 'vitest';
import { UserProvider, useCurrentUser } from '../../src/context/UserContext';

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <UserProvider>{children}</UserProvider>
);

describe('useCurrentUser', () => {
  test('starts null when localStorage is empty', () => {
    const { result } = renderHook(() => useCurrentUser(), { wrapper });
    expect(result.current.username).toBeNull();
  });

  test('reads existing username from localStorage on mount', () => {
    localStorage.setItem('bbs:username', 'alice');
    const { result } = renderHook(() => useCurrentUser(), { wrapper });
    expect(result.current.username).toBe('alice');
  });

  test('setUsername persists to localStorage and updates state', () => {
    const { result } = renderHook(() => useCurrentUser(), { wrapper });

    act(() => {
      result.current.setUsername('bob');
    });

    expect(result.current.username).toBe('bob');
    expect(localStorage.getItem('bbs:username')).toBe('bob');
  });

  test('setUsername(null) removes from localStorage', () => {
    localStorage.setItem('bbs:username', 'carol');
    const { result } = renderHook(() => useCurrentUser(), { wrapper });

    act(() => {
      result.current.setUsername(null);
    });

    expect(result.current.username).toBeNull();
    expect(localStorage.getItem('bbs:username')).toBeNull();
  });

  test('cross-tab sync: storage event from another tab updates state', () => {
    const { result } = renderHook(() => useCurrentUser(), { wrapper });
    expect(result.current.username).toBeNull();

    // Simulate another tab writing to localStorage. Real storage events
    // fire in OTHER tabs, not the one that wrote — so we dispatch manually.
    act(() => {
      window.dispatchEvent(
        new StorageEvent('storage', {
          key: 'bbs:username',
          newValue: 'dave',
          oldValue: null,
        }),
      );
    });

    expect(result.current.username).toBe('dave');
  });

  test('storage event for an unrelated key is ignored', () => {
    localStorage.setItem('bbs:username', 'alice');
    const { result } = renderHook(() => useCurrentUser(), { wrapper });

    act(() => {
      window.dispatchEvent(
        new StorageEvent('storage', {
          key: 'some-other-app:setting',
          newValue: 'changed',
        }),
      );
    });

    expect(result.current.username).toBe('alice');
  });
});
