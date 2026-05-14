# BBS Frontend — Micah Briggs (A4)

React + TypeScript + Vite frontend for the A2 BBS Webserver.

## How to run

In one terminal, the backend (this repo's A2):

```bash
cd assignments/bbs-webserver/rmbriggs
# activate venv
uvicorn main:app --port 8000
```

In another, the frontend:

```bash
cd assignments/bbs-frontend/rmbriggs
npm install
npm run dev
```

Open http://localhost:5173. The backend URL is configurable:

```bash
VITE_API_BASE=http://example.com:8000 npm run dev
```

Default is `http://localhost:8000`.

## Tier targeted

**Gold.** Bronze + silver + three gold items.

## Changes I made to my A2 backend

Added `CORSMiddleware` allowing `http://localhost:5173`, because browsers refuse cross-origin requests unless the server opts in. One-liner per the FastAPI CORS docs. No other backend changes.

## Design decisions

- **Hooks layer over inline fetches.** Every page consumes a hook (`useFeed`, `usePost`, `useUsers`, `useBoards`, `useCurrentUser`), not raw `useEffect(fetch(...))`. This centralizes loading/error/data state, gives one place to add polling and optimistic updates, and keeps pages thin. The default agent move is inline fetches sprinkled through components, which would have turned `FeedPage` into a 200-line god component.
- **Routing.** `react-router-dom` v7. Seven routes: `/`, `/login`, `/users`, `/users/:username`, `/posts/:id`, `/boards`, `/boards/:name`, plus a 404. All bookmarkable; back button works because each page is its own route. `Layout` is a single `<Outlet/>` wrapper that renders nav + current-user pill on every page.
- **Optimistic POST with `client_id` reconciliation.** `useFeed.createPost` immediately prepends a draft `{client_id, status: 'pending'}` to a separate `optimistic` array. On 201, the draft is removed by `client_id` and the server post merged into `posts`. On 4xx/5xx, the draft is removed and the error is surfaced inline. Importantly the optimistic array is separate from committed `posts`, so the 3s polling refetch can't double-render the new post.
- **Polling, not push.** 3s `setInterval` in `useFeed`, paused when `document.visibilityState === 'hidden'`. Polling instead of SSE/websockets because (a) zero backend change, (b) BBS traffic is low enough that 3s latency is fine, (c) the request is a single GET that returns ≤20 posts — cheap.
- **X-Username "not real auth," as a visible preference.** `localStorage.username` drives the header. The current username appears in the nav as a pill, never hidden. The login page has no password field because pretending we have one would lie about the security model; the page literally explains "Identity is just a header — not real auth." Mutations are disabled in the UI when no username is set.

## Gold items

1. **Real-time-ish polling** — `useFeed` refetches every 3s, paused on hidden tab. Posts from another tab appear within ~3s. See `src/hooks/useFeed.ts`.
2. **Visual design with a point of view** — type scale of 5 sizes (12/14/16/20/28), one accent color (neutral 900), generous spacing on a 4px grid via Tailwind defaults, mobile-first layout that holds at 320px wide.
3. **Invented UI feature: threads + reactions + boards-as-navigation** — A2 supports all three; A4 wires them into a single coherent UI. Click a post → `/posts/:id` shows the thread tree (`ThreadView` recursively renders `/posts/{id}/thread`). Each `PostCard` has a `ReactionBar` for heart/laugh/fire with optimistic upsert (A2 has one-reaction-per-user semantics). The `BoardsPage` lists boards; `BoardPage` is a board-scoped feed with its own compose box that auto-fills the `board` field.

## Tests

```bash
npm test
```

Vitest + React Testing Library. 26 tests covering the most logic-heavy components (`ComposeBox`, `useFeed`, `ReactionBar`) plus foundation tests for `apiFetch`, `useApi`, `useCurrentUser`. Per repo convention, each test case is its own named function — no parametrize.

## Where my agent helped most and where I had to push back

The agent was great at scaffolding the layout (Vite + Tailwind + router boilerplate in ~5 minutes) and at translating the design doc's hook signatures into working code. Where I had to push back: (1) the default plan put `fetch` calls inline in each page; I argued it into a hooks layer because otherwise the 22-endpoint surface would have meant 22 ad-hoc loading patterns. (2) The initial optimistic POST implementation kept the draft inside the committed `posts` array, which meant polling could race-replace it; I separated them into a parallel `optimistic` list reconciled by a `client_id`. (3) Loading/error states were the recurring miss — the agent shipped the happy path and skipped the empty states and 404 views; I had to enumerate every fetch site and demand the three states uniformly. Most of bronze polish was me clicking around finding "click delete twice fast" type bugs and writing them up.
