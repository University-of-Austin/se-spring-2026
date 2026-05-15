# JBBS — BBS Frontend (Emessjay)

A React + TypeScript + Vite frontend for the BBS API from A2, with a synthwave dark visual identity.

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

## Test commands

```
npm test           # Vitest unit + component tests (one-shot)
npm run test:watch # Vitest in watch mode
npm run test:e2e   # Playwright end-to-end user-flow test
```

- **Vitest**: 4 files, 28 assertions covering the trickiest pieces — `apiFetch` error envelopes, `useApi`'s stale-fetch protection, `<Loadable>`'s four branches, the `usernameValidity` truth table.
- **Playwright**: 1 spec, runs the full user flow (create user → sign out → switch back via dropdown → post a message → see it in the feed → click into detail → delete → verify gone). The Playwright config auto-starts both the A2 backend (via `../.venv/bin/uvicorn`) and the Vite dev server, so `npm run test:e2e` works as a single command.

## Tier targeted

**Gold.** Silver feature set in full, plus two gold items:

- **Real automated tests that prove the user flow** ([`tests/e2e/user-flow.spec.ts`](tests/e2e/user-flow.spec.ts)).
- **Visual design with a point of view** — synthwave dark, Orbitron typography, dual neon accents (purple / green) for primary actions and navigation respectively, layered text-shadow glows on accent surfaces, a fixed grid background + horizon vignette, hot-pink danger states.

Silver features carried over:

- Real routing via `react-router-dom`. URLs like `/`, `/users`, `/users/alice`, `/posts/42`, `/compose`, `/identity` are bookmarkable and survive a refresh; the back button works.
- Optimistic posting: a new message appears at the top of the feed immediately with a "sending…" muted style, transitions to a green-tinted "posted ✓" state for a brief crossover, then disappears as the server response refetches. Failed posts get a hot-pink-bordered "failed to send" entry with Retry/Dismiss actions and the server's error detail.
- Pagination UX: `IntersectionObserver` watches a sentinel near the bottom of the feed and loads the next page automatically; "Load more" stays as the keyboard / no-IO fallback.
- Keyboard shortcuts beyond Cmd+Enter: Gmail-style `g`-prefix navigation (`g f`/`g c`/`g u`/`g i`), `n` for new post, `/` to focus feed search, `?` for help overlay, `Esc` to close.
- Accessibility: real `<Link>` and `<button>` semantics throughout (no `div`s pretending to be buttons), every input has a `<label>` (visually-hidden where appropriate), skip-to-main-content link, focus-visible rings on every interactive element, `<NavLink>` provides `aria-current="page"` automatically.

## Design decisions

- **One `apiFetch` chokepoint.** Every fetch in the app goes through [`src/api/client.ts`](src/api/client.ts). The function normalises A2's single-string `{"detail": "..."}` envelope into an `ApiError` class with `{status, detail}` — so a 422 lands as the same shape as a 404, and downstream UI is simple. Network failures (fetch rejection) become `ApiError` with `status: 0` so views render "backend not reachable" the same way they render any other error.

- **Custom hooks over a query library.** [`src/hooks/useApi.ts`](src/hooks/useApi.ts) is a generic `{data, loading, error, refetch}` primitive; the per-resource hooks (`usePosts`, `useUser`, …) are one-liners on top of it. I deliberately did *not* reach for TanStack Query — the assignment asks me to handle loading / error / cache myself, and writing it makes the trade-offs visible. The hook uses an `ignore` flag + `AbortController` on cleanup so a stale response from a previous deps value can't overwrite newer state. [`useApi.test.tsx`](src/hooks/useApi.test.tsx) pins this behavior down with a deliberately-ordered deferred-promise test.

- **`<Loadable>` is the only path to rendering data.** Every view passes its `useApi` result to [`src/components/Loadable.tsx`](src/components/Loadable.tsx) and gives it a render-prop for the success case. The component renders a spinner on first load, an error block (with a "Try again" button wired to `refetch()`) on failure, an optional 404 view when `error.status === 404`, and an empty state when `data` is `[]`. You literally cannot map over data in a view without going through this component — which is the structural answer to the assignment's warning about agents shipping `data.map(...)` with no guards.

- **Optimistic posts via a shared context.** [`src/hooks/useOptimisticPosts.tsx`](src/hooks/useOptimisticPosts.tsx) owns the post lifecycle because the POST is fired from `ComposeView` but resolves after we've navigated away to the feed. A pending entry is rendered at the top in muted style ("sending…"); on success it briefly glows green ("posted ✓") and bumps a `feedVersion` that triggers `usePosts` to refetch — the real post arrives, then the optimistic entry is removed via a 1.5s timeout so the hand-off reads as intentional. On failure the entry stays with a hot-pink border, the server's error detail, and a Retry button that hits the same endpoint again.

- **A typed `paths` helper instead of literal route strings.** [`src/router/paths.ts`](src/router/paths.ts) exports `paths.user(name)`, `paths.post(id)`, etc. A route rename is a one-line change with TypeScript pointing at every caller. URL encoding happens once in the helper.

- **A leader-key shortcut system.** [`src/hooks/useShortcuts.tsx`](src/hooks/useShortcuts.tsx) installs one global `keydown` listener. Gmail-style `g`-prefix nav is a `useRef` to a `{active, expiresAt}` state — the second key has 1 second to land. Shortcuts are suppressed while the user is typing into an `INPUT` / `TEXTAREA` / `SELECT` / contenteditable, except `?` (always active).

- **Identity surfaced visibly.** [`src/hooks/useCurrentUser.tsx`](src/hooks/useCurrentUser.tsx) reads/writes `localStorage.bbs.username` and exposes it through a Context. The header reads "posting as @alice" (in glowing neon green) on every page — the X-Username "not real auth" reality is kept visible so the user can't lose track of which name will go on their next post.

- **Synthwave design with shared tokens.** [`src/index.css`](src/index.css) defines a small set of CSS custom properties — surface colours, the two accent neons (purple `#b026ff`, green `#39ff14`), hot-pink danger states, and three named glow shadows. Every component CSS module references these. Orbitron is the only typeface, used at four weights for a coherent type system; uppercase letter-spaced labels evoke a CRT readout. A fixed body grid + radial horizon glow sits behind everything via `body::before`. Primary CTAs are solid green with a green halo; navigation and links are purple; danger is hot pink with its own halo — a deliberate three-channel colour language that makes the next action obvious without reading the label. Tested at 320px width.

## Changes I made to my A2 backend

- **Added `CORSMiddleware`** to [`../../bbs-webserver/Emessjay/webserver/main.py`](../../bbs-webserver/Emessjay/webserver/main.py), pinned to `allow_origins=["http://localhost:5173"]` with `allow_methods=["*"]` and `allow_headers=["*"]`. Pinning the origin is the least-privilege default; `allow_headers=["*"]` is required so the browser's preflight `OPTIONS` accepts the custom `X-Username` header.

## Where my agent helped most and where I had to push back

Claude did the bulk of the file-writing once I'd settled the architecture with it. The biggest push-back was on **loading/error scaffolding**: by default it produced views that called `usePosts()` and then `posts.map(...)`, which works exactly until the network blinks. I pushed for a single `<Loadable>` render-prop component that views *must* go through to render data, which makes the bug structurally impossible. The second push-back was on **stale-fetch handling** in `useApi` — the obvious effect doesn't cancel the previous request, and Claude's first draft would have let a slow response for "ab" overwrite a fresh response for "abc". I asked for the `ignore` flag + `AbortController` cleanup specifically and made sure the comments explain *why*. For optimistic posting, the temptation was to fire the POST from the compose view itself; I moved it into a context so the network call doesn't die when the view unmounts on navigate. Claude was good at the layout/CSS scaffolding once I gave it design tokens to work from — it stopped producing inconsistent spacing as soon as the tokens existed in `index.css`. For the Playwright spec, I had to argue against asserting on visible text during route transitions: the optimistic entry and the real server entry both render the same message simultaneously, and using `getByText` triggers a strict-mode locator violation. The fix was to use semantically-distinct readiness signals (`getByRole("link", { name })` for the real post, the Delete button as the post-detail readiness signal).

## Gold-tier rationale

1. **Real automated tests that prove the user flow** ([`tests/e2e/user-flow.spec.ts`](tests/e2e/user-flow.spec.ts)). Covers `create user → sign-out → switch back via dropdown → post → see in feed → click into detail → delete → verify gone` — all the named beats from the assignment. The Playwright config's `webServer` array auto-starts both the FastAPI backend (via the A2 `.venv` so we don't depend on the user's global uvicorn) and the Vite dev server, with `reuseExistingServer: !CI` so the test hooks into already-running dev processes rather than fighting over ports. Each run uses time-ordered + random unique usernames so tests don't collide with each other or with the existing DB.

2. **Visual design with a point of view.** Synthwave dark, anchored on Orbitron + a dual-neon palette (purple primary, green secondary, hot pink for danger). Tokens-driven so a change to the look is one place. Layered text-shadow glow on accent text, a fixed body grid with a radial purple horizon vignette, uppercase tracked labels for forms — the design has a position, not just a colour swap.

## Project layout

```
src/
  api/            ← types.ts, client.ts (apiFetch + ApiError), endpoints.ts
  hooks/          ← useApi, useCurrentUser, useOptimisticPosts, useShortcuts,
                    usePosts, usePost, useUsers, useUser, useDebouncedValue
  router/         ← paths.ts (typed URL builders)
  components/     ← Loadable, PostRow, PendingPostRow, UserLink, Timestamp,
                    Spinner, ApiErrorMessage, NotFoundView, Header, ShortcutsHelp
  views/          ← FeedView, ComposeView, UserListView, UserProfileView,
                    PostDetailView, IdentityView
  test/           ← setup.ts (vitest + jest-dom)
  App.tsx         ← BrowserRouter + Routes + global providers + skip link
  index.css       ← design tokens, Orbitron, body grid background
tests/
  e2e/            ← Playwright user-flow spec
```

Vitest tests live next to the file they test (`Foo.test.tsx` alongside `Foo.tsx`). Playwright specs are in `tests/e2e/`.

## A note on production routing

Because routing is client-side, refreshing `/posts/42` in production requires the static host to serve `index.html` as the fallback for unknown paths. `npm run dev` and `npm run preview` already do this; any deployment target (Vercel, Netlify, S3+CloudFront, nginx) needs an equivalent rewrite rule.
