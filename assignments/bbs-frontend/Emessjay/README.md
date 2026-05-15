# JBBS — BBS Frontend (Emessjay)

A React + TypeScript + Vite frontend for the BBS API from A2, in a Miami-sunset / outrun visual idiom.

## How to run

You need **two processes**: the A2 backend on `:8000` and this frontend on `:5173`.

**Terminal 1 — A2 backend**
```
cd ../../bbs-webserver/Emessjay/webserver
# activate the A2 venv (or use .venv/bin/uvicorn directly)
uvicorn main:app --port 8000
```

**Terminal 2 — JBBS frontend**
```
cd assignments/bbs-frontend/Emessjay
npm install
npm run dev
```

Vite prints a URL like `http://localhost:5173`. Open it.

The backend URL is read from `VITE_API_BASE`, defaulting to `http://localhost:8000`. Override at boot time for a different host:
```
VITE_API_BASE=https://my-deployed-bbs.example.com npm run dev
```

## Tier targeted

**Gold.** Silver feature set in full, plus two gold items: **visual design with a point of view** and **real-time-ish updates**. A Playwright user-flow spec is also included as part of the silver test bar.

## Test commands

```
npm test           # Vitest unit + component tests (one-shot)
npm run test:watch # Vitest in watch mode
npm run test:e2e   # Playwright end-to-end user-flow test
```

- **Vitest**: 4 files, 28 assertions covering the trickiest pieces — [`apiFetch`](src/api/client.ts) error-envelope normalisation, [`useApi`](src/hooks/useApi.ts)'s stale-fetch protection, [`<Loadable>`](src/components/Loadable.tsx)'s four branches, the `usernameValidity` truth table.
- **Playwright**: 1 spec in [`tests/e2e/user-flow.spec.ts`](tests/e2e/user-flow.spec.ts), running the full user flow (create user → sign out → switch back via dropdown → post a message → see it in the feed → click into detail → delete → verify gone). The Playwright config auto-starts both the A2 backend (via `../.venv/bin/uvicorn`) and the Vite dev server, so `npm run test:e2e` works as a single command.

Silver features carried over:

- Real routing via `react-router-dom`. URLs like `/`, `/users`, `/users/alice`, `/posts/42`, `/compose`, `/identity` are bookmarkable and survive a refresh; the back button works.
- Optimistic posting: a new message appears at the top of the feed immediately with a "sending…" muted style, transitions to a green-tinted "posted ✓" state for a brief crossover, then is swapped out the moment the real row arrives from the next refetch.
- Pagination UX: `IntersectionObserver` watches a sentinel near the bottom of the feed and loads the next page automatically; "Load more" stays as the keyboard / no-IO fallback.
- Keyboard shortcuts beyond Cmd+Enter: Gmail-style `g`-prefix navigation (`g f`/`g c`/`g u`/`g i`), `n` for new post, `/` to focus feed search, `?` for help overlay, `Esc` to close.
- Accessibility: real `<Link>` and `<button>` semantics throughout (no `div`s pretending to be buttons), every input has a `<label>` (visually-hidden where appropriate), skip-to-main-content link, focus-visible rings on every interactive element, `<NavLink>` provides `aria-current="page"` automatically.

## Design decisions

- **One `apiFetch` chokepoint.** Every fetch in the app goes through [`src/api/client.ts`](src/api/client.ts). The function normalises A2's single-string `{"detail": "..."}` envelope into an `ApiError` class with `{status, detail}` — so a 422 lands as the same shape as a 404, and downstream UI is simple. Network failures (fetch rejection) become `ApiError` with `status: 0` so views render "backend not reachable" the same way they render any other error.

- **Custom hooks over a query library.** [`src/hooks/useApi.ts`](src/hooks/useApi.ts) is a generic `{data, loading, error, refetch}` primitive; the per-resource hooks (`usePosts`, `useUser`, …) are one-liners on top of it. I deliberately did *not* reach for TanStack Query — the assignment asks me to handle loading / error / cache myself, and writing it makes the trade-offs visible. The hook uses an `ignore` flag + `AbortController` on cleanup so a stale response from a previous deps value can't overwrite newer state. [`useApi.test.tsx`](src/hooks/useApi.test.tsx) pins this behavior down with a deliberately-ordered deferred-promise test.

- **`<Loadable>` is the only path to rendering data.** Every view passes its `useApi` result to [`src/components/Loadable.tsx`](src/components/Loadable.tsx) and gives it a render-prop for the success case. The component renders a spinner on first load, an error block (with a "Try again" button wired to `refetch()`) on failure, an optional 404 view when `error.status === 404`, and an empty state when `data` is `[]`. You literally cannot map over data in a view without going through this component — which is the structural answer to the assignment's warning about agents shipping `data.map(...)` with no guards.

- **Routing via a typed `paths` helper instead of literal strings.** [`src/router/paths.ts`](src/router/paths.ts) exports `paths.user(name)`, `paths.post(id)`, etc. A route rename is a one-line change with TypeScript pointing at every caller. URL encoding happens once in the helper.

- **Optimistic posts via a shared context.** [`src/hooks/useOptimisticPosts.tsx`](src/hooks/useOptimisticPosts.tsx) owns the post lifecycle because the POST is fired from `ComposeView` but resolves after we've navigated away to the feed. A pending entry is rendered at the top in muted style ("sending…"); on success the context records the server-assigned real `id` and bumps `feedVersion` to trigger a `usePosts` refetch. The feed view filters out any pending entry whose `confirmedId` is now present in the live list — so the optimistic row hands off cleanly to the real one rather than briefly double-rendering. On failure the pending entry stays with a hot-pink border, the server's error detail, and Retry/Dismiss actions.

- **Real-time-ish updates by polling.** [`src/hooks/usePoll.ts`](src/hooks/usePoll.ts) calls `refetch` on a 5-second interval and is used by [`FeedView`](src/views/FeedView.tsx) so a post from user B appears in user A's open feed within the budget the assignment specifies. Because `useApi` keeps the existing `data` on screen during a refetch (only `loading` flips), the row list just updates in place — no spinner flash. Polling pauses on `document.visibilitychange` (hidden tab → no requests) and fires one immediate catch-up refetch the moment the tab becomes visible again, so the user sees fresh data on the same beat they re-focus.

- **A leader-key shortcut system.** [`src/hooks/useShortcuts.tsx`](src/hooks/useShortcuts.tsx) installs one global `keydown` listener. Gmail-style `g`-prefix nav is a `useRef` to a `{active, expiresAt}` state — the second key has 1 second to land. Shortcuts are suppressed while the user is typing into an `INPUT` / `TEXTAREA` / `SELECT` / contenteditable, except `?` (always active).

- **Identity surfaced visibly.** [`src/hooks/useCurrentUser.tsx`](src/hooks/useCurrentUser.tsx) reads/writes `localStorage.bbs.username` and exposes it through a Context. The header reads "posting as @alice" on every page — the `X-Username` "not real auth" reality is kept visible so the user can't lose track of which name will go on their next post. The Identity view is also the only place a username is *created or switched*, so the user always sees the full state of the choice rather than picking up an implicit one.

- **Miami-sunset visual identity with shared tokens.** [`src/index.css`](src/index.css) defines a small set of CSS custom properties — surface colours, the two accent neons (purple `#b026ff`, green `#39ff14`), hot-pink danger states, three named glow shadows. Every component CSS module references these. A fixed full-viewport sunset sky (sun, water-reflection ellipse, horizon glow, navy→pink gradient) sits behind everything on a `body::before`, the outrun perspective floor on `body::after`, and a mirrored sky-grid on `html::before` — three pseudo-element layers stacked at negative z-indices so they don't catch pointer events. Orbitron is the only typeface, used at four weights with uppercase tracked labels for form fields. Tested at 320px width.

## Why polling, not SSE / websockets

The assignment explicitly allows polling and asks for a one-line justification: A2 is a REST-only FastAPI app, and adding server-sent events or a websocket endpoint there would be more invasive than the gold tier asks for. A 5-second polling cadence on a low-traffic feed is within the assignment's "~5 seconds" budget and costs one cheap `GET /posts` per tick. Pausing on tab-hide keeps idle background tabs from making the wrong trade-off. If this app ever needed sub-second freshness or had a thousand concurrent viewers, SSE would beat polling on both latency and aggregate request volume — but at this scale the simpler primitive is the right one.

## Changes I made to my A2 backend

- **Added `CORSMiddleware`** to [`../../bbs-webserver/Emessjay/webserver/main.py`](../../bbs-webserver/Emessjay/webserver/main.py), pinned to `allow_origins=["http://localhost:5173"]` with `allow_methods=["*"]` and `allow_headers=["*"]`. Pinning the origin is the least-privilege default; `allow_headers=["*"]` is required so the browser's preflight `OPTIONS` accepts the custom `X-Username` header.

## Where my agent helped most and where I had to push back

Claude did the bulk of the file-writing once I'd settled the architecture with it. The biggest push-back was on **loading/error scaffolding**: by default it produced views that called `usePosts()` and then `posts.map(...)`, which works exactly until the network blinks. I pushed for a single `<Loadable>` render-prop component that views *must* go through to render data, which makes the bug structurally impossible. The second push-back was on **stale-fetch handling** in `useApi` — the obvious effect doesn't cancel the previous request, and Claude's first draft would have let a slow response for "ab" overwrite a fresh response for "abc"; I asked for the `ignore` flag + `AbortController` cleanup specifically and made sure the comments explained *why*. For optimistic posting, the temptation was to fire the POST from the compose view itself; I moved it into a context so the network call doesn't die when the view unmounts on navigate. Claude also wanted the optimistic row to time out on a fixed 1.5s schedule after success, which double-rendered with the real row for a beat — I pushed for an id-based handoff (record `confirmedId`, drop the pending entry the moment that id shows up in the live list). For polling, the first draft was a naked `setInterval` in `FeedView`; I argued it out into a reusable hook and added the `visibilitychange` pause + on-return catch-up refetch so hidden tabs don't keep firing GETs. Claude was good at the layout/CSS scaffolding once I gave it design tokens to work from — it stopped producing inconsistent spacing as soon as the tokens existed in `index.css`. For the Playwright spec, I had to argue against asserting on visible text during route transitions: the optimistic entry and the real server entry both render the same message simultaneously, and using `getByText` triggers a strict-mode locator violation. The fix was to use semantically-distinct readiness signals (`getByRole("link", { name })` for the real post, the Delete button as the post-detail readiness signal).

## Gold-tier rationale

1. **Visual design with a point of view.** A Miami-sunset / outrun visual identity built from three stacked CSS pseudo-element layers: a full-viewport sunset sky on `body::before` (navy→pink gradient, dome-only sun anchored at a 60vh horizon, a flattened water-reflection ellipse beneath the sun), an outrun perspective floor on `body::after` (cyan/pink grid with a mask that fades it into the horizon so the lines don't terminate in a hard edge), and a mirrored sky-grid on `html::before` (same construction, rotation inverted so the vanishing point sits *at* the horizon). All three layers sit at negative z-indices and `pointer-events: none`, so they're decoration that catches no clicks. Above that the UI uses a strict three-channel colour language — green for primary CTAs (post, confirm), purple for navigation and links, hot pink for danger — with a small set of named glow shadows shared via CSS custom properties. Orbitron at four weights with uppercase tracked labels is the only typeface. Tested at 320px width.

2. **Real-time-ish updates.** The feed polls `GET /posts` every 5 seconds via [`usePoll`](src/hooks/usePoll.ts) so a post from user B appears in user A's open feed within the assignment's ~5s budget. The polling hook pauses while the tab is hidden (no requests from backgrounded tabs) and fires one immediate catch-up refetch the moment the tab becomes visible again. Because `useApi` keeps existing `data` on screen across refetches, the row list updates in place with no spinner flash, and the optimistic-post id-based handoff means a user's own pending row stays put until the very refetch that contains it — no double-render, no flicker. The README section above explains why polling beats SSE / websockets at this scale.

## Project layout

```
src/
  api/            ← types.ts, client.ts (apiFetch + ApiError), endpoints.ts
  hooks/          ← useApi, useCurrentUser, useOptimisticPosts, useShortcuts,
                    usePosts, usePost, useUsers, useUser, useDebouncedValue, usePoll
  router/         ← paths.ts (typed URL builders)
  components/     ← Loadable, PostRow, PendingPostRow, UserLink, Timestamp,
                    Spinner, ApiErrorMessage, NotFoundView, Header, ShortcutsHelp
  views/          ← FeedView, ComposeView, UserListView, UserProfileView,
                    PostDetailView, IdentityView
  test/           ← setup.ts (vitest + jest-dom)
  App.tsx         ← BrowserRouter + Routes + global providers + skip link
  index.css       ← design tokens, Orbitron, sunset + grid background layers
tests/
  e2e/            ← Playwright user-flow spec
```

Vitest tests live next to the file they test (`Foo.test.tsx` alongside `Foo.tsx`). Playwright specs are in `tests/e2e/`.

## A note on production routing

Because routing is client-side, refreshing `/posts/42` in production requires the static host to serve `index.html` as the fallback for unknown paths. `npm run dev` and `npm run preview` already do this; any deployment target (Vercel, Netlify, S3+CloudFront, nginx) needs an equivalent rewrite rule.
