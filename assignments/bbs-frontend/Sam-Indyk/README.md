# BBS Frontend — Sam-Indyk

React + TypeScript + Vite app on top of [my A2 BBS API](../../bbs-webserver/SamIndyk/).

## Tier targeted: **Gold**

- Bronze: ✅ all six views, every A2 bronze endpoint wired, loading/error/empty states everywhere, client- and server-side validation, `localStorage` identity persistence.
- Silver: ✅ React Router with real bookmarkable URLs, optimistic post-create with rollback, "Load more" pagination, three+ keyboard shortcuts (`Ctrl/⌘+Enter`, `g f`, `g u`, `g a`, `?`), 23 vitest+RTL tests, basic accessibility (real `<label>`s, focus-visible rings, no `<div>`-as-button).
- Gold: ✅ picked **two of four** —
  - **Real-time-ish updates.** Feed polls `/posts` every 5 s. `usePolling` only fires while the tab is visible (`visibilitychange`) and the browser reports online (`navigator.onLine`), so a backgrounded tab doesn't pile up requests. Polling pauses while a search filter is active, on the theory that "live updates" make less sense over a narrowed result set than over the open firehose.
  - **Visual design with a point of view.** Terminal-BBS-flavored: monospace headings, a single amber accent, deliberate type scale (1.25 minor third) and 4-pt spacing scale exposed as CSS custom properties. Light mode tracks `prefers-color-scheme`. Layout collapses cleanly to 320 px (single-column user list, smaller heading scale). Focus rings are double-stroked so they read on either theme.

## How to run

You need **two terminals**.

### 1. Backend (A2)

```sh
cd assignments/bbs-webserver/SamIndyk
pip install -r requirements.txt
uvicorn main:app --port 8000 --host 127.0.0.1
```

### 2. Frontend (this app)

```sh
cd assignments/bbs-frontend/Sam-Indyk
npm install
npm run dev
```

Vite serves on `http://localhost:5173`. Open it in a browser.

### Environment

- `VITE_API_BASE` — backend base URL. Defaults to `http://localhost:8000`. To point at a deployed backend: `VITE_API_BASE=https://bbs.example.com npm run dev`.

### Changes I made to my A2 backend

- **Added `CORSMiddleware`** (`main.py`). Without it the browser blocks every fetch from `:5173` to `:8000`. Whitelist is just `http://localhost:5173` and `http://127.0.0.1:5173`; allow_credentials is `false` so the wildcard isn't needed.
- That's the only change. The API contract is otherwise unchanged from A2.

## Design decisions

1. **Hooks layer, not inline fetches.** Every page goes through a single `useApi(fetcher, deps)` hook that returns `{ data, loading, error, refetch, setData }` and handles `AbortController` cancellation on unmount or dep-change. This means "show a loading state, show an error, retry" is a uniform two-line treatment instead of being re-derived on each page. `setData` is exposed so the feed can do an optimistic prepend without re-fetching.
2. **Optimistic posts use a synthetic negative id.** The composer hands the parent a `Post` with a negative `id` (a counter that monotonically decreases) before the network call returns. The feed renders pending posts above real ones with a "posting…" tag and `aria-busy="true"`. When the server responds, the parent prepends the real post (with a real positive id) and drops the placeholder; on failure, the placeholder is dropped, a danger toast appears, and the textarea text is restored so the user doesn't lose their draft. The "did the real twin land?" matcher in the feed uses `(username, message, ~30 s of created_at)` so the row doesn't briefly duplicate after the next poll.
3. **`X-Username` is treated as a soft identity, in the UI too.** There's no password field anywhere. The "Sign in" flow is literally "pick a username from a list, or type one to create." That matches the A2 contract (X-Username is a header, not auth). The post-detail page exposes a Delete button to anyone for the same reason — pretending otherwise would be theater. The README and the auth page both call this out so it's not a surprise.
4. **Routing structure.** Five routes: `/`, `/users`, `/users/:username`, `/posts/:id`, `/auth`, plus a 404 catch-all. Search state lives in the URL as `?q=`, so a search is bookmarkable and survives a refresh. `useSearchParams` from react-router-dom; no global store needed.
5. **Polling is in a hook, not in the page.** `usePolling(fn, intervalMs, enabled)` owns the interval, the visibility-change wiring, the online/offline wiring, and the cleanup. Pages just call `usePolling(refetch, 5000, !filtered)`. Splitting the policy from the action makes both easy to test in isolation.

## Where my agent helped most and where I had to push back

The agent (Claude) was great at the first draft of each page — given a spec line like "user profile with their posts, 404 view if missing" it produced the layout and the happy-path data wiring quickly. Where I had to push back: it kept wanting to write components that did `data.map(...)` directly with no guard for `data === null`, and on error its instinct was to silently render an empty list. The loading/error/empty triple appears on **every** view in this app because I explicitly demanded the scaffolding before any happy-path code went in. The 422 error path was another one — the first cut just showed "fetch failed" instead of parsing FastAPI's `detail` array; surfacing the actual server message ("String should have at least 1 character") took an explicit follow-up. The optimistic-update reconciliation logic (matching real-twin posts against pending ones, so the feed doesn't briefly double after a poll) also needed me to think through the race myself — the agent's first version replaced by index, which broke as soon as anything else arrived between the optimistic prepend and the server response.

## Tests

```sh
npm test          # one-shot vitest run
npm run test:watch
```

23 tests across 5 files, ~5 s wall clock:

- `tests/client.test.ts` — API client behavior: query-string construction, header forwarding, 422 detail-array parsing, 204 short-circuit, network-failure wrapping.
- `tests/useUser.test.tsx` — `localStorage` persistence and cross-hook sync via the custom `bbs:user-changed` event.
- `tests/PostRow.test.tsx` — rendering of meta, "(edited)" tag, pending state, URL-safe author links.
- `tests/Compose.test.tsx` — sign-in guard, disabled button on empty, character count + over-limit class, optimistic submit → real post reconciliation, rollback on 422 with text restored.
- `tests/FeedPage.test.tsx` — happy-path render, error banner on fetch failure, `?q=` search URL flow, empty state.

## Keyboard shortcuts

| Key                 | Action                  |
| ------------------- | ----------------------- |
| `Ctrl/⌘ + Enter`    | Submit a draft post     |
| `g` then `f`        | Go to feed              |
| `g` then `u`        | Go to users             |
| `g` then `a`        | Go to sign-in           |
| `?`                 | Toggle shortcut overlay |

Shortcuts ignore keys typed inside `<input>` / `<textarea>` so they don't interfere with composing.
