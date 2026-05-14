# BBS Frontend (A4) — Design

**Owner:** Micah Briggs
**Due:** Fri 2026-05-15, 5:00pm
**Tier targeted:** Gold (3 picks: real-time-ish polling, visual design with POV, invented UI feature)
**Location:** `assignments/bbs-frontend/rmbriggs/`
**Backend:** own A2 at `assignments/bbs-webserver/rmbriggs/` on `http://localhost:8000`

## Goal

A React + TypeScript + Vite frontend for the A2 BBS Webserver, hitting Gold tier within a two-day window. The grade depends more on visible polish (loading/error states, validation, edge-case behavior, code organization, visual taste) than on feature count, so the design optimizes for clean bronze foundation first, then layered gold work.

## Tier targets

- **Bronze (25 pts):** all six views, all eight A2 bronze endpoints wired, visible loading/error states everywhere, client-side validation surfacing server 422s, identity persisted via `localStorage`, default `VITE_API_BASE`.
- **Silver (8 pts):** react-router-dom for real URLs; optimistic POST /posts with rollback on failure; "load more" pagination on A2's cursor; ≥1 keyboard shortcut beyond Cmd+Enter; ≥3 Vitest tests; basic a11y (labels, keyboard reachability).
- **Gold (7 pts):** three picks — real-time-ish polling on the feed; visual design with a coherent POV; an "invented UI feature" implemented as threads + reactions + boards-as-navigation against A2's existing endpoints.

## Stack

- **Build:** Vite, React 18, TypeScript.
- **Routing:** `react-router-dom` v6.
- **Styling:** Tailwind CSS + shadcn/ui primitives.
- **Tests:** Vitest + React Testing Library.
- **Backend contract:** A2 with `CORSMiddleware` added for `http://localhost:5173`.

## Project layout

```
assignments/bbs-frontend/rmbriggs/
  src/
    api/
      client.ts          # fetch wrapper: VITE_API_BASE, X-Username, error normalization
      types.ts           # User, Post, Board, Reaction
    hooks/
      useApi.ts          # generic { data, loading, error, refetch }
      useFeed.ts         # cursor pagination + 3s polling + optimistic posts
      usePost.ts         # single post + thread
      useUsers.ts        # list + single user
      useBoards.ts       # list + single board + board feed
      useCurrentUser.ts  # localStorage-backed identity, surfaced via context
    components/
      PostCard.tsx       # post + reactions + thread expand toggle
      ReactionBar.tsx    # heart/laugh/fire pickers with optimistic update
      ThreadView.tsx     # recursive thread render
      ComposeBox.tsx     # textarea + char count + Cmd+Enter + 422 surfacing
      UserPill.tsx       # clickable username
      LoadingRow.tsx
      ErrorBox.tsx
      Layout.tsx         # nav + current-user switcher + board sidebar
    pages/
      FeedPage.tsx       # /
      UsersPage.tsx      # /users
      UserPage.tsx       # /users/:username
      PostPage.tsx       # /posts/:id   (renders ThreadView)
      BoardsPage.tsx     # /boards
      BoardPage.tsx      # /boards/:name
      LoginPage.tsx      # /login
      NotFound.tsx       # 404 view
    App.tsx              # router config only
    main.tsx
  tests/
    ComposeBox.test.tsx
    useFeed.test.ts
    ReactionBar.test.tsx
  public/
  index.html
  package.json
  tsconfig.json
  vite.config.ts
  tailwind.config.ts
  components.json        # shadcn config
  README.md
  .env.example           # VITE_API_BASE=http://localhost:8000
```

## Architecture

### Fetch layer (`src/api/client.ts`)

Single fetch wrapper used everywhere. Responsibilities:

- Read base URL from `import.meta.env.VITE_API_BASE` (default `http://localhost:8000`).
- Inject `X-Username` header from `useCurrentUser` when set.
- Parse JSON; on non-2xx, normalize to a typed error `{ status, detail }` where `detail` is the FastAPI `detail` field (string or list-of-objects for 422) — never swallowed.
- Throw on network failure; hooks translate to error state.

No retry, no caching at this layer. One responsibility.

### Hooks layer (`src/hooks/`)

Every page consumes a hook, not a raw fetch. Each hook owns:

- the fetch lifecycle (`loading`, `error`, `data`),
- any cursor / pagination state it needs,
- any optimistic-update state it owns,
- and exposes mutation functions (`createPost`, `addReaction`, `deletePost`).

**Why a hooks layer instead of inline `useEffect`.** The spec calls this out specifically as where agents cut corners. Centralizing avoids 8 different loading patterns, 8 different error patterns, and 8 places to add polling. Also keeps `App.tsx` and pages thin (style/quality grade).

**`useApi`** — generic hook taking a URL + options, returning `{ data, loading, error, refetch }`. Used directly by the read-only hooks; composed by the mutating ones.

**`useFeed`** — wraps a cursor-paginated feed. Owns:
- `posts` (committed from server),
- `optimisticPosts` (client-only entries with a `client_id`),
- `cursor` / `hasMore` for load-more,
- `setInterval(refetch, 3000)` while mounted, paused on `document.visibilitychange === 'hidden'`,
- mutation `createPost(message)` that pushes an optimistic entry and reconciles on response.

**`usePost`** — `GET /posts/{id}` and `GET /posts/{id}/thread`. Exposes `deletePost(id)`.

**`useUsers`, `useBoards`** — list + single-resource fetches.

**`useCurrentUser`** — reads `localStorage.getItem('username')` on mount, exposes `{ username, setUsername, clearUsername }`. Provided via `UserContext` at the root.

### Optimistic update model (POST /posts)

1. User submits in `ComposeBox` → calls `createPost(message)` from `useFeed`.
2. Hook appends `{ client_id, username, message, created_at: now, status: 'pending' }` to `optimisticPosts`, returned merged at top of feed.
3. `client.ts` POST; on 201, replace the optimistic entry (matched by `client_id`) with the server response and remove from `optimisticPosts`.
4. On 4xx/5xx, remove the optimistic entry and surface error inline in `ComposeBox` (422 `detail` rendered verbatim).
5. Polling that arrives mid-flight does not duplicate the new post — committed posts are de-duplicated by `id`, and the optimistic entry has no server `id` until it's replaced.

### Routing (`react-router-dom`)

| Path | Page |
|---|---|
| `/` | FeedPage |
| `/login` | LoginPage (create/switch user) |
| `/users` | UsersPage |
| `/users/:username` | UserPage |
| `/posts/:id` | PostPage |
| `/boards` | BoardsPage |
| `/boards/:name` | BoardPage |
| `*` | NotFound |

All bookmarkable. Back button works. `Layout` wraps all routes and renders nav + current-user pill + board sidebar.

### Identity model

`X-Username` is not real auth. The frontend treats it as a *preference* persisted in `localStorage`. UX implications:

- `LoginPage` lets the user create (`POST /users`) or switch (set `localStorage`). No password field — that would lie about the security model.
- The current username is visible in `Layout` so it is never hidden whose identity is being sent. Clicking it opens a switch dropdown.
- Mutations that require identity (POST /posts, PATCH, DELETE, reactions) are disabled in the UI when no username is set, with a "sign in to post" affordance pointing at `/login`.

### Loading / error / empty conventions

Every fetch site shows one of three states. Helpers:

- `LoadingRow` — neutral skeleton row used in lists.
- `ErrorBox` — title + `detail` message + a "retry" button calling the hook's `refetch`.
- Empty states are explicit per page ("no posts yet", "no users yet", "this user hasn't posted") — never blank.

22 endpoint surfaces × these three states is where most agent slop lives. The hooks layer enforces them uniformly.

### Form validation

| Field | Client rule | Behavior |
|---|---|---|
| Username | `^[a-zA-Z0-9_]+$`, 3–20 chars | Submit disabled until match. |
| Post message | 1–500 chars | Submit disabled when empty. Live char count, red past 500. |
| Bio (if used) | 0–200 chars | Live char count. |

Any server 422 is rendered inline with the raw `detail.msg`. Never eaten.

### Gold: real-time-ish polling

`useFeed` schedules a `setInterval(refetch, 3000)` while mounted on `/`. Pauses when `document.visibilityState === 'hidden'` to avoid burning requests on background tabs. Polling-not-push because: (a) A2 doesn't expose SSE/websockets, (b) BBS traffic is low enough that 3s latency is fine, (c) zero backend change.

### Gold: visual design POV

Tailwind config sets a deliberate scale:
- type: 12 / 14 / 16 / 20 / 28 (5 sizes, no more),
- spacing: stick to Tailwind's `1 / 2 / 3 / 4 / 6 / 8 / 12 / 16` and don't invent custom values,
- color: a single neutral grayscale plus one accent for primary actions; no decorative color,
- layout: mobile-first; works at 320px wide; sidebar collapses below `md`.

Goal: feels deliberately designed, not "tailwind defaults thrown together."

### Gold: invented UI feature (threads + reactions + boards)

Three integrated UI surfaces against existing A2 endpoints. Implemented in `PostCard` and `ThreadView` so they layer onto the feed naturally.

- **Threads.** `PostCard` has an "expand thread" toggle when `parent_id IS NULL` and the post has descendants (detected via a thread-presence hint — see "Open questions" below). `PostPage` shows the full thread tree; `ThreadView` renders recursively from the flat `/posts/{id}/thread` response. Reply button on each post posts with `parent_id` set.
- **Reactions.** `ReactionBar` on every `PostCard` showing counts for `heart`, `laugh`, `fire`. Clicking a kind sends `POST /posts/{id}/reactions`; immediately updates local count (optimistic, with rollback); clicking the kind you already reacted with sends DELETE; clicking a different kind upserts (A2 already supports this as one-reaction-per-user upsert).
- **Boards as navigation.** Sidebar lists boards from `GET /boards`. Clicking a board navigates to `/boards/:name` which uses the existing board-scoped feed. Compose box has a board selector (defaults to "no board"). Posting to a nonexistent board surfaces the A2 404 inline.

### Pagination UX

"Load more" button at the bottom of the feed. Uses A2's cursor envelope (`{ posts, next_cursor, has_more }`). On click, fetch with current `cursor`, append posts. Chosen over numbered pages because BBS is sequential; chosen over infinite-scroll because it's easier to do correctly under polling.

### Keyboard

- `Cmd/Ctrl + Enter` in compose textarea — submits.
- `/` anywhere (when focus not in an input) — jumps to search box.
- `?` overlay — shortcut cheatsheet.

## Backend changes to A2

1. Add `CORSMiddleware` in `assignments/bbs-webserver/rmbriggs/main.py` allowing `http://localhost:5173`. Per the FastAPI CORS docs snippet.
2. Document the change in both A2's and A4's README.

No other changes anticipated. If a bug surfaces during use, fix in A2 and note it in the A4 README ("changes I made to my A2 backend").

## Tests (Vitest + React Testing Library)

Three tests, each its own named `function test_...()`, no `parametrize`:

1. **`tests/ComposeBox.test.tsx`** — `test_compose_box_disables_submit_when_empty`, `test_compose_box_shows_red_char_count_past_500`, `test_compose_box_surfaces_server_422_detail`.
2. **`tests/useFeed.test.ts`** — `test_use_feed_starts_in_loading_state`, `test_use_feed_transitions_to_success_with_posts`, `test_use_feed_transitions_to_error_on_500`.
3. **`tests/ReactionBar.test.tsx`** — `test_reaction_bar_renders_counts`, `test_reaction_bar_optimistic_update_on_click`, `test_reaction_bar_rolls_back_on_500`.

Run via `npm test`.

## Risk register

- **CORS surprise on A2.** Test the wired-up CORS middleware in the first 30 minutes; symptom is "fetch fails with no detail in console." Mitigation: add CORS first, hit `GET /users` from the browser console manually to confirm.
- **Polling colliding with optimistic POST.** Mitigation: tag optimistic entries with `client_id`; merge by `id` for committed entries, never duplicate.
- **Threading + reactions both touching `PostCard`.** Mitigation: design `PostCard`'s props for both from the start; don't retrofit reactions onto a thread-aware card later.
- **Visual design eats Friday AM.** Mitigation: hard time-box to 2 hours; ship what's there if it runs over. Tests > polish on the margin.
- **A2 needs to be running for development.** Mitigation: keep two terminals open; first thing every session is verify backend is up.

## Schedule

Two days, ~15 hours.

| Block | Hours | Work |
|---|---|---|
| Wed eve | 2 | Branch from `bbs-webserver-rmbriggs` to `bbs-frontend-rmbriggs`. Scaffold Vite + Tailwind + shadcn + router. Add CORS to A2. `api/client.ts`, `types.ts`. `useCurrentUser` + LoginPage. |
| Thu AM | 3 | `useFeed` + FeedPage with load-more + polling. `ComposeBox` with optimistic POST. `PostCard` scaffold. |
| Thu PM | 3 | `useUsers` + UsersPage + UserPage. `usePost` + PostPage + `ThreadView`. Reply box. |
| Thu eve | 2 | `ReactionBar` with optimistic reactions. `useBoards` + BoardsPage + BoardPage. Board picker in compose. |
| Fri AM | 2 | Visual design pass: typography, color, spacing, mobile width. Layout polish. |
| Fri PM | 2 | Three Vitest tests. README. Edge-case clickthrough: double-click submit, empty form, network off, refresh persistence, 422 surfacing. |
| Fri 4–5pm | 1 | Buffer + PR. |

## README requirements (A4)

1. How to run (`npm install`, `npm run dev`, `VITE_API_BASE`, A2 CORS note).
2. Tier targeted: Gold.
3. Design decisions (≥4 bullets): routing (react-router with the 7 routes), optimistic POST strategy (`client_id` reconciliation), polling vs push (3s setInterval, why polling over SSE), how X-Username "not real auth" is exposed in the UI (visible pill, switch flow, no password lie).
4. Where the agent helped most and where I pushed back (one paragraph).
5. Test command (`npm test`). Gold item sentences (polling, visual design POV, invented UI feature).

## Open questions

- **Thread-presence hint on a post.** A2's post shape includes `id`, `username`, `message`, `created_at`, `updated_at`, `board`, `reaction_counts`, `parent_id`. There is no `reply_count`. The frontend either (a) calls `/posts/{id}/thread` lazily on expand (preferred; one extra fetch per opened thread) or (b) the A2 API gains a `reply_count` field (small backend change, noted in README if taken). Resolution: ship (a); only add `reply_count` if the lazy approach feels slow during clickthrough.

## What we are explicitly NOT building

- Auth (passwords, JWTs).
- A global store (Redux, Zustand, React Query).
- Service workers / PWA.
- Server-sent events or websockets.
- Drag-and-drop, dark mode, mentions-as-links, Playwright e2e.
- Anything beyond the three chosen gold items.
