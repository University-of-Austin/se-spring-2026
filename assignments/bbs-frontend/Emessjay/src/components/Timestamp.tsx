// Renders a server timestamp as a relative time ("3m ago") that
// updates as the user lingers, with the full ISO time as a tooltip
// for anyone who wants exactness.
//
// A2 sends ISO-8601 UTC strings without explicit timezone — Date()
// in modern browsers will parse those as UTC.  We confirm by reading
// the string and treating a missing Z as UTC.

import { useEffect, useState } from "react";

function parseServerTime(iso: string): Date {
  // Ensure trailing Z so it's parsed as UTC even if missing.
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + "Z");
}

function relative(date: Date, now: Date): string {
  const diffMs = now.getTime() - date.getTime();
  const sec = Math.round(diffMs / 1000);
  if (sec < 5) return "just now";
  if (sec < 60) return `${sec}s ago`;
  const min = Math.round(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.round(hr / 24);
  if (day < 7) return `${day}d ago`;
  return date.toLocaleDateString();
}

export function Timestamp({ iso }: { iso: string }) {
  const date = parseServerTime(iso);
  const [now, setNow] = useState(() => new Date());

  // Re-render once a minute so "3m ago" doesn't get stale.  Stops
  // when the tab is hidden — see why this matters in setInterval
  // docs (background tabs throttle).
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);

  return (
    <time dateTime={iso} title={date.toLocaleString()}>
      {relative(date, now)}
    </time>
  );
}
