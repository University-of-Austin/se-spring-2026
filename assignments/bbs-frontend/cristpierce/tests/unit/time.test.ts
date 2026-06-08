import { describe, expect, it } from 'vitest'
import { relativeTime } from '../../src/lib/time'

// Parsed as local time, same as the values under test, so the deltas are
// timezone-independent.
const NOW = new Date('2026-06-08T12:00:00').getTime()

describe('relativeTime', () => {
  it('says "just now" for under 5 seconds', () => {
    expect(relativeTime('2026-06-08T11:59:58', NOW)).toBe('just now')
  })
  it('formats seconds', () => {
    expect(relativeTime('2026-06-08T11:59:30', NOW)).toBe('30s ago')
  })
  it('formats minutes', () => {
    expect(relativeTime('2026-06-08T11:30:00', NOW)).toBe('30m ago')
  })
  it('formats hours', () => {
    expect(relativeTime('2026-06-08T09:00:00', NOW)).toBe('3h ago')
  })
  it('formats days', () => {
    expect(relativeTime('2026-06-05T12:00:00', NOW)).toBe('3d ago')
  })
  it('clamps small future skew to "just now"', () => {
    expect(relativeTime('2026-06-08T12:01:00', NOW)).toBe('just now')
  })
  it('returns empty string for an unparseable date', () => {
    expect(relativeTime('not-a-date', NOW)).toBe('')
  })
})
