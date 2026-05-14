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

1. **CORS middleware** allowing `http://localhost:5173`, because browsers refuse cross-origin requests unless the server opts in. One-liner per the FastAPI CORS docs.
2. **`GET /posts/stream` SSE endpoint** for the real-time gold pick. Module-level subscriber registry (set of `(asyncio.Queue, optional_board_filter)` tuples). The stream endpoint yields `data: tick\n\n` per message and `: heartbeat\n\n` every 15s of idle so proxies don't close it. Known limit: subscribers are per-process, so this would not survive `uvicorn --workers N` without a real broker (Redis pubsub or similar).
3. **SSE ticks on every mutation that affects what's visible**, not just `POST /posts`. The endpoints `POST/DELETE /posts/{id}/reactions/*`, `PATCH /posts/{id}`, and `DELETE /posts/{id}` all now call the notifier with the affected post's board so other tabs refetch within a frame. Without this, reactions and edits only propagated on the next unrelated post.
4. **`sort=newest|oldest|trending` on `GET /posts`**. Default is now `newest` (`ORDER BY p.id DESC`, cursor compares `<`), fixing a mismatch where the A2 docs said newest-first but the implementation was actually oldest-first. `trending` reuses the A1 time-decayed reply score `replies / (hours + 2)^1.2` (see `cmd_trending` in `assignments/bbs/rmbriggs/bbs_db.py`).
5. **Soft-deleted usernames are recyclable.** `delete_user` now renames the soft-deleted user to `[deleted_<id>]` (brackets keep it out of the create-user regex's `^[a-zA-Z0-9_]+$`) and drops the user's reactions, so a future user registering the freed name doesn't silently inherit them. The A2 README's original "names aren't recycled" reasoning was about impersonation in old conversations — that's still handled because posts JOIN on `user_id`, and the `CASE WHEN u.deleted_at IS NOT NULL THEN '[deleted]'` substitution keeps old posts attributed to `[deleted]` even after the name is reclaimed by a different user.

## Design decisions

- **Hooks layer over inline fetches.** Every page consumes a hook (`useFeed`, `usePost`, `useApi`, `useCurrentUser`, `useTheme`), not raw `useEffect(fetch(...))`. This centralizes loading/error/data state, gives one place to add SSE and optimistic updates, and keeps pages thin. The default agent move is inline fetches sprinkled through components, which would have turned `FeedPage` into a 200-line god component.
- **Routing.** `react-router-dom` v7. Seven routes — `/`, `/login`, `/users`, `/users/:username`, `/posts/:id`, `/boards`, `/boards/:name` — plus a 404. All bookmarkable; back button works because each page is its own route. `Layout` is a single `<Outlet/>` wrapper that renders nav + current-user pill + theme toggle on every page. The outlet is keyed by `location.pathname` so each navigation triggers a 220ms fade-in animation.
- **Optimistic mutations with reconciliation.** Three flavors. (1) `useFeed.createPost` immediately prepends a draft `{client_id, status: 'pending'}` to a **separate** `optimistic` array — separate so the SSE refetch can't double-render the new post — and reconciles by `client_id` on 201. (2) `PostCard` tracks the user's local reaction kind so switching ♥→😂 decrements the previous and increments the new (A2 uses one-reaction-per-user upsert semantics; without local tracking the UI couldn't decrement). After the POST a small GET reconciles drift. (3) Delete optimistically hides the card; rollback on failure restores it with the server `detail` inline.
- **SSE push on every mutation, not polling.** `useFeed` and `usePost` open `EventSource` connections to `GET /posts/stream` (with `?board=<name>` for board-scoped pages). The A2 backend keeps a per-subscriber `asyncio.Queue` and fans out `data: tick\n\n` on every mutation that affects what's rendered — `POST /posts`, `POST/DELETE /reactions`, `PATCH /posts/{id}`, `DELETE /posts/{id}`. Sub-second latency, idle tabs cost zero requests. In-memory single-process pub/sub, so it wouldn't survive `uvicorn --workers N` without a real broker — called out in the A2 changes section.
- **Sort options with cursor direction flipping.** `GET /posts?sort=newest|oldest|trending`. Newest (default) reverses the cursor comparison (`p.id < :cursor_id` instead of `>`), oldest is the original behavior, trending reuses my A1 time-decayed reply score (`replies / (hours + 2)^1.2`). FeedPage and BoardPage both expose a `<select>` next to the search box.
- **Design tokens via CSS variables + Tailwind v4 `@theme inline`.** Color, radius, shadow, and font all flow from `src/index.css` variables exposed as Tailwind utilities (`bg-card`, `text-muted-foreground`, `border-border`, `bg-primary`, `text-destructive`, etc.). Light + dark palettes both defined; `.dark` on `<html>` flips them. A `useTheme` hook persists the choice in localStorage and falls back to `prefers-color-scheme`. The header has a sun/moon toggle.
- **X-Username "not real auth," as a visible preference.** `localStorage.username` drives the header. The current username appears in the nav as a pill (and links to your profile), never hidden. The login page has no password field because pretending we have one would lie about the security model; the page literally explains "Identity is just a header — not real auth." Mutations are disabled in the UI when no username is set.

## Gold items

The spec asks for at least two of four. Ended up doing all four because each one pulled the next into scope.

1. **Real-time-ish push (SSE)** — both `useFeed` and `usePost` subscribe to `GET /posts/stream` via `EventSource`; the A2 backend pushes a tick on every mutation that affects what's rendered (posts, reactions, edits, deletes), board-filtered per subscriber. Sub-second cross-tab propagation. See `src/hooks/useFeed.ts`, `src/hooks/usePost.ts`, and the `# ── SSE stream ──` block in `main.py`.
2. **Visual design with a point of view** — full shadcn-style design-token sheet in `src/index.css` (light + dark palettes via `oklch()`, semantic tokens for surface/foreground/muted/primary/destructive/border, radius and shadow ramps), Tailwind v4 `@theme inline` exposing them as utilities, mobile-first layout that holds at 320px wide, manual sun/moon dark-mode toggle in the header, six small CSS-only animations (page transition, hover lift on cards, reaction count bounce, theme color transition, optimistic-post fade-in, smooth reply-expand via CSS grid `0fr → 1fr`).
3. **Invented UI feature: threads + reactions + boards + sort + trending** — A2 supports all of these; A4 stitches them into a single coherent UI. Click anywhere on a `PostCard` → `/posts/:id` shows the thread tree (`ThreadView` recursively renders `/posts/{id}/thread`); reply/delete inline; `ReactionBar` for ♥/😂/🔥 with optimistic upsert. The Feed and Board pages have a sort selector (Newest/Oldest/Trending) using my A1 time-decayed reply score for trending. Inline create-board form on `/boards`. Delete-account button on your own profile (the A2 soft-delete renames you to `[deleted_<id>]` so the username can be recycled).
4. **Real automated tests that prove the user flow** — Playwright spec at `tests/e2e/bbs.spec.ts`. Three tests: the canonical gold-tier flow (create user → switch → post → see in feed → delete), inline 422 surfacing on overlength messages, and optimistic-then-settled reaction counts. The Playwright config auto-spawns both the FastAPI backend and the Vite dev server if they're not already running. `npm run test:e2e` is the one command.

## Tests

Two suites — unit/hook tests via Vitest, end-to-end flow via Playwright.

```bash
npm test          # Vitest: 27 tests across hooks/components/api
npm run test:e2e  # Playwright: end-to-end user flow against a live backend + frontend
```

The Vitest suite covers `apiFetch`, `useApi`, `useCurrentUser`, `useFeed` (including SSE), `ComposeBox`, and `ReactionBar` — 27 tests, named-function-per-case style.

The Playwright suite at `tests/e2e/bbs.spec.ts` covers the gold-tier flow: create user → switch to that user → post a message → see it in the feed → delete it. It also asserts inline-422 surfacing on overlength messages and optimistic-then-reconciled reaction updates. The config auto-starts the FastAPI backend (`python3 -m uvicorn`) and the Vite dev server (`npm run dev`) if they aren't already running. First run needs `npx playwright install chromium` (~100MB Chromium download).

## Where my agent helped most and where I had to push back

The agent was great at the mechanical work — scaffolding the stack in five minutes, translating the design doc's hook signatures into working code, faithfully implementing complex SQL (the trending query that uses SQLite's `julianday()` + `pow()` for the time-decay reply score landed correctly on the first try once I pointed at the A1 formula). Specialized work like the recursive `WITH RECURSIVE` thread CTE on the backend or the CSS-grid `0fr → 1fr` trick for animating the reply expand were both the agent's first-draft choices and they were correct.

Where I had to push back, roughly in order:

- **Scaffolding picked the wrong stack on first run.** `npx shadcn@latest init` pulled v4 (which expects Tailwind v4 + Base UI), but the plan pinned Tailwind v3. The agent didn't notice that the resulting `src/index.css` had `@apply border-border outline-ring/50` referencing classes Tailwind v3 couldn't resolve. Dev server returned HTTP 200 — but `vite build` failed loudly with `CssSyntaxError`. Had to strip shadcn entirely (we never imported any of its primitives anyway). Later, when I pasted in a real shadcn-style design-token CSS, we did the full Tailwind v3 → v4 migration cleanly. Lesson: HTTP 200 from `npm run dev` isn't the same as "the build works."
- **Inline fetches in every page.** The agent's default architecture put `fetch` directly in each page component. With 22 endpoint surfaces, that meant 22 ad-hoc loading patterns. I argued it into a hooks layer (`useApi`, `useFeed`, `usePost`, `useCurrentUser`, `useTheme`) so loading/error/data lives in one place per resource type. This single decision is probably what kept the rest of the project from spiraling.
- **Optimistic POST kept the draft inside the committed posts array.** First implementation pushed the new post directly onto `posts` and tried to mark it pending. With SSE refetching the feed mid-flight, this races: the refetch arrives, the server's version replaces the optimistic version, except sometimes you get a brief duplicate. Split into a parallel `optimistic` array reconciled by `client_id`. Now polling can't disturb in-flight optimistics.
- **Loading/error states were a recurring miss.** Agent shipped happy paths and skipped empty states, 404 views, offline rollback. Even after I established the pattern early, regressions kept appearing — when I added reactions to `PostCard` later, the error message was `"Couldn't react: 422"` (raw status code) instead of surfacing the `detail` field the spec explicitly calls out. Required a separate audit pass to walk every fetch site and confirm all three states (loading + success + error-with-detail) were visible.
- **SSE was only wired to POST /posts.** I asked for polling → SSE; first cut wired only `POST /posts`. Reactions in tab A never propagated to tab B. I had to explicitly say "everything that should be a server-side event should be a server-side event" before the agent fanned out the notifier across `POST/DELETE /reactions`, `PATCH /posts`, and `DELETE /posts`.
- **PostCard's local state ignored refetched props.** Reaction counts were initialized via `useState(post.reaction_counts)` — initializer only runs once. When useFeed refetched, the new `post` props were ignored and the counts stayed stale until manual reload. Needed an explicit `useEffect` to sync on prop change.
- **Reactions didn't decrement the previous kind on switch.** A2's reactions are `UNIQUE(post_id, username)` — switching from ♥ to 😂 replaces server-side, but the optimistic client just incremented 😂 without decrementing ♥. Two stale counts until refresh. Added local "myKind" tracking + a reconcile GET after the POST.
- **Trending implementation didn't match the one I'd already built.** Said "make a trending page" and the agent went with raw reaction count desc. I'd already designed a time-decayed reply score in my A1 (`replies / (hours_since_post + 2)^1.2`) and wanted that. Had to point at `assignments/bbs/rmbriggs/bbs_db.py:cmd_trending` for the exact SQL. Then I changed my mind and wanted trending as an inline sort option instead of a separate page — agent rebuilt as a `<select>` cleanly.
- **Animation polish took two passes.** The first optimistic-post fly-in was a 240ms `translateY(-12px) → 0` keyframe. Optimistic POSTs usually resolve in under 100ms, so the animation got cut off mid-flight and the layout shift was visibly janky. Worse, the keyframe's final `opacity: 1` fought with the static `opacity-60` class meant to indicate the pending state. Replaced with a 120ms pure-opacity fade landing exactly at 0.6 (the pending dim), so the keyframe's "to" state and the static dim agree. No layout shift.
- **Reply button placement was cramped on own posts.** When I added the delete button (only visible on your own posts), I conditionally toggled the reply button's `ml-auto` based on ownership, which produced "reply  delete" on the right when you owned the post but ended up squeezing reply against the timestamp. Cleaner fix: wrap both reply and delete in a single right-aligned cluster, always positioned the same regardless of ownership.
- **Reasoned-from-first-principles vs ergonomics on username recycling.** My A2 README explicitly argued deleted usernames shouldn't be recycled to prevent impersonation in old conversations. When I asked the agent to let me recreate my own deleted account in A4, it surfaced that earlier reasoning before reversing it — which was the right move. The fix renames the soft-deleted row to `[deleted_<id>]` (brackets keep it out of the create-user regex) and drops the user's reactions so they don't silently transfer to whoever claims the freed name. The original impersonation concern is still handled because posts JOIN on `user_id` and the `CASE WHEN deleted_at IS NOT NULL THEN '[deleted]'` substitution keeps old posts attributed to `[deleted]`.

The throughline: the agent will ship code that works at the demo level. Real product polish — propagation, edge cases, animation timing, error-message specificity, consistency across the surface area — takes specific instructions per item. The README question is genuinely useful as a tool here; writing this list made me notice that the loading/error audit was the single biggest payoff for the time invested, because it caught five separate gaps the agent had introduced incrementally and never been forced to revisit.
