/**
 * IdentityContext: persists the "current username" preference across reloads.
 * Pulled out as a context (not a hook + module global) so tests can render with
 * a known starting state without monkey-patching localStorage every time.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { IdentityProvider, useIdentity } from '../../src/identity/IdentityContext';

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <IdentityProvider>{children}</IdentityProvider>
);

describe('IdentityContext', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('starts with no username when localStorage is empty', () => {
    const { result } = renderHook(() => useIdentity(), { wrapper });
    expect(result.current.username).toBeNull();
  });

  it('hydrates username from localStorage on mount', () => {
    localStorage.setItem('bbs:username', 'alice');
    const { result } = renderHook(() => useIdentity(), { wrapper });
    expect(result.current.username).toBe('alice');
  });

  it('persists username to localStorage when set', () => {
    const { result } = renderHook(() => useIdentity(), { wrapper });
    act(() => result.current.setUsername('bob'));
    expect(result.current.username).toBe('bob');
    expect(localStorage.getItem('bbs:username')).toBe('bob');
  });

  it('clears username when set to null', () => {
    localStorage.setItem('bbs:username', 'carol');
    const { result } = renderHook(() => useIdentity(), { wrapper });
    act(() => result.current.setUsername(null));
    expect(result.current.username).toBeNull();
    expect(localStorage.getItem('bbs:username')).toBeNull();
  });
});
