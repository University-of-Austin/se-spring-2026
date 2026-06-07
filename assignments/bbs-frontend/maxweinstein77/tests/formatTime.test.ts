// Tests the relative-time helper. Pure function -- no React needed.

import { describe, expect, it } from "vitest";
import { formatRelativeTime } from "../src/lib/formatTime";

function isoSecondsAgo(secs: number): string {
  return new Date(Date.now() - secs * 1000).toISOString();
}

describe("formatRelativeTime", () => {
  it("returns 'just now' for the present moment", () => {
    expect(formatRelativeTime(isoSecondsAgo(1))).toBe("just now");
  });

  it("returns seconds-ago for a recent past", () => {
    expect(formatRelativeTime(isoSecondsAgo(30))).toBe("30s ago");
  });

  it("returns minutes-ago after 60 seconds", () => {
    expect(formatRelativeTime(isoSecondsAgo(120))).toBe("2m ago");
  });

  it("returns hours-ago after an hour", () => {
    expect(formatRelativeTime(isoSecondsAgo(2 * 3600))).toBe("2h ago");
  });

  it("returns days-ago after a day", () => {
    expect(formatRelativeTime(isoSecondsAgo(3 * 86400))).toBe("3d ago");
  });

  it("falls back to absolute date for anything older than a week", () => {
    // 8 days ago -- should use locale date, not "Xd ago"
    const result = formatRelativeTime(isoSecondsAgo(8 * 86400));
    expect(result).not.toMatch(/ago/);
    // Just check it parses as a real date.
    expect(new Date(result).toString()).not.toBe("Invalid Date");
  });
});
