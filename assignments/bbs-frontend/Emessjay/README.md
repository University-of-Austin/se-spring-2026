# BBS Frontend — Emessjay

A React + TypeScript + Vite frontend for the BBS API from A2.

## How to run

You need **two processes**: the A2 backend on `:8000` and this frontend on `:5173`.

**Terminal 1 — A2 backend**
```
cd ../../bbs-webserver/Emessjay/webserver
# activate the A2 venv
uvicorn main:app --port 8000
```

**Terminal 2 — A4 frontend**
```
cd assignments/bbs-frontend/Emessjay
npm install
npm run dev
```

Vite prints a URL like `http://localhost:5173`. Open it.

The backend URL is read from `VITE_API_BASE`, defaulting to `http://localhost:8000`. Override at boot time if you need to point at a different host, e.g.:
```
VITE_API_BASE=https://my-deployed-bbs.example.com npm run dev
```

## Tier targeted

**Bronze.** All six views implemented and reachable, all eight A2 bronze endpoints wired up, every fetch shows loading / error / empty states, client-side validation plus server-422 surfacing on the compose form, identity persisted via `localStorage`.

The architecture is also structured so that silver-tier work (real routing, optimistic updates, tests) can be layered in without rewriting components — see "Design decisions" below.

## Design decisions

- **One `apiFetch` chokepoint.** Every fetch in the app goes through [`src/api/client.ts`](src/api/client.ts). Views and hooks never see raw `Response` objects, never construct URLs, and never repeat themselves on error parsing. The function normalises A2's single-string `{"detail": "..."}` error envelope into an `ApiError` class with `{status, detail}` — so a 422 from the server lands as the same shape as a 404, and downstream UI is simple. Network failures (fetch rejection) become `ApiError` with `status: 0` so views can render "backend not reachable" the same way they render any other error.

- **Custom hooks over a query library.** [`src/hooks/useApi.ts`](src/hooks/useApi.ts) is a generic `{data, loading, error, refetch}` primitive; the per-resource hooks (`usePosts`, `useUser`, …) are one-liners on top of it. I deliberately did *not* reach for TanStack Query — the assignment specifically asks me to handle loading / error / cache myself, and writing it makes the trade-offs visible. The hook uses an `ignore` flag + `AbortController` on cleanup so a stale response from a previous deps value can't overwrite newer state (e.g. typing fast in the search box).

- **`<Loadable>` is the only path to rendering data.** Every view passes its `useApi` result to [`src/components/Loadable.tsx`](src/components/Loadable.tsx) and gives it a render-prop for the success case. The component renders a spinner during the first load, an error block (with a "Try again" button that calls `refetch()`) on failure, and an optional 404 view when `error.status === 404`. This is the structural answer to the assignment's warning about agents shipping `data.map(...)` with no guards — you literally cannot map over data in a view without going through this component.

- **A router seam, not a real router (yet).** [`src/router/useRouter.tsx`](src/router/useRouter.tsx) exposes `{route, navigate}` where `route` is a tagged union. Bronze backs this with a single `useState`; URLs don't change as you navigate. The point of the seam is that the silver-tier swap to `react-router-dom` is a local replacement of this file — `useNavigate()` and `useParams()` would slot into the same call sites. Views consume the API, not the implementation.

- **Identity via `localStorage` + Context, surfaced visibly.** [`src/hooks/useCurrentUser.tsx`](src/hooks/useCurrentUser.tsx) reads/writes `localStorage.bbs.username` and exposes it through a Context so views don't prop-drill. The chrome at the top of every page reads "Posting as @alice" (or "not signed in") — the goal is to make the X-Username "not real auth" reality visible to the user at all times, instead of letting them forget which name they're impersonating. Sign-out is a one-button affordance in the Identity view.

- **Design tokens.** [`src/index.css`](src/index.css) defines color/spacing/type-scale custom properties; every component CSS module references them. This is also the seat of a future dark-mode toggle: redeclaring the same tokens under `[data-theme="dark"]` would flip the whole UI.

## Changes I made to my A2 backend

- **Added `CORSMiddleware`** to [`../../bbs-webserver/Emessjay/webserver/main.py`](../../bbs-webserver/Emessjay/webserver/main.py), pinned to `allow_origins=["http://localhost:5173"]` with `allow_methods=["*"]` and `allow_headers=["*"]`. Pinning the origin (instead of using `"*"`) is the least-privilege default; `allow_headers=["*"]` is required so the browser's preflight `OPTIONS` request passes the custom `X-Username` header without me having to enumerate every header by hand.

(If I discover additional A2 issues while using the frontend, they'll be fixed in A2 and listed here.)

## Where my agent helped most and where I had to push back

Claude (via Claude Code) did the bulk of the file-writing once I'd settled the architecture with it. The big push-back was on **loading/error scaffolding**: by default it produced views that called `usePosts()` and then `posts.map(...)`, which works exactly until the network blinks. I pushed for a single `<Loadable>` render-prop component that views *must* go through to render data, which makes the bug structurally impossible. The other place I had to argue is **stale-fetch handling** in `useApi` — the obvious effect doesn't cancel the previous request, and Claude's first draft would have let a slow response for "ab" overwrite a fresh response for "abc". I asked for the `ignore` flag + `AbortController` cleanup specifically, and made sure the code comments explain *why* that pattern is there so I can defend it. Claude was good at the layout/CSS scaffolding once I gave it design tokens to work from — it stopped producing wildly inconsistent spacing as soon as the tokens existed in `index.css`.

## Project layout

```
src/
  api/            ← types.ts, client.ts (apiFetch + ApiError), endpoints.ts
  hooks/          ← useApi, useCurrentUser, usePosts, usePost, useUsers, useUser, useDebouncedValue
  router/         ← useRouter (the silver-swap seam)
  components/     ← Loadable, PostRow, UserLink, Timestamp, Spinner, ApiErrorMessage, NotFoundView
  views/          ← FeedView, ComposeView, UserListView, UserProfileView, PostDetailView, IdentityView
  App.tsx         ← top-level providers + nav + view dispatch
  index.css       ← design tokens
```
