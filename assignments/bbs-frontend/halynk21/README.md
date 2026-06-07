# BBS Frontend — Assignment 4

**Software Engineering · UATX · Spring 2026 · halynk21**

> A real React app over the FastAPI BBS from A2.
> Routing, polling, dark mode, optimistic delete, an E2E spec, and design tokens that survive `prefers-color-scheme`.

---

## Tier targeted

**Gold** — all six Silver requirements + three of the four Gold items (real-time-ish polling, dark mode with `system` support, Playwright E2E that scripts the rubric's exact named flow).

---

## How to run

You'll have **two processes** going during dev — one for the A2 backend, one for this frontend. Two terminals.

### Terminal 1 — A2 backend

```bash
cd assignments/bbs-webserver/halynk21
# activate the A2 venv however you set it up (this is the same venv from A2)
uvicorn main:app --port 8000
```

### Terminal 2 — A4 frontend

```bash
cd assignments/bbs-frontend/halynk21
npm install
npm run dev
```

Vite prints a URL like `http://localhost:5173`. Open that in a browser.

### Configuration

The frontend reads the backend URL from `VITE_API_BASE`, defaulting to `http://localhost:8000`. Override at the command line if your A2 lives elsewhere:

```bash
VITE_API_BASE=https://my-bbs.example.com npm run dev
```

### Changes I made to my A2 backend

`assignments/bbs-webserver/halynk21/main.py` — added `CORSMiddleware` to allow requests from `http://localhost:5173` (the Vite dev server's origin). This is the standard CORS opt-in described in the FastAPI docs; without it the browser refuses to let JavaScript on `:5173` see responses from `:8000`. The middleware allows all methods and all headers (including the custom `X-Username`) and does not enable credentials, since `X-Username` is not a session cookie.

No A2 endpoint behaviour, validation, or response shape was changed.

---

## Tests

### Unit (Vitest + RTL)

```bash
npm run test       # watch mode
npm run test:run   # one-shot CI mode
```

Three test files under `tests/unit/`:

- **`validate.test.ts`** — username regex + length boundaries; post length boundaries; submittable predicates.
- **`useCurrentUser.test.tsx`** — initial read from `localStorage`, set/persist round-trip, sign-out clearing, cross-tab sync via `storage` events, ignores unrelated keys.
- **`PostForm.test.tsx`** — submit-disabled-when-empty; enabled-after-typing; **inline 422 surfacing** (the server's `fieldErrors.message` shows under the textarea, wired with `aria-describedby` and `aria-invalid` — not a toast); `Cmd+Enter` submits; textarea clears after success.

### End-to-end (Playwright — Gold)

```bash
npm run test:e2e:install    # one-time, ~100MB chromium download
npm run test:e2e            # runs the spec; auto-starts npm run dev
```

Playwright auto-starts the Vite dev server via `webServer`. The A2 backend must be running separately on `http://localhost:8000` (same two-terminal model the assignment setup uses).

The spec at `tests/e2e/flow.spec.ts` runs the Gold-rubric flow word-for-word: **create user → switch to that user → post a message → see it in the feed → delete it.** The "switch" step is real — the test signs out between create and switch so it isn't merely the auto-sign-in side effect of create. Two smaller specs cover client-side validation (empty post → submit disabled) and search URL-sync (`?q=` updates after debounce).

---

## Design decisions

### 1. Routing — `react-router-dom` v7, six routes

- `/` — feed (search, compose, load more)
- `/users` — list of all users
- `/users/:username` — profile with posts (polled)
- `/posts/:id` — single post + delete
- `/login` — combined create + switch user
- `*` — `NotFoundPage` (route doesn't exist)

URLs are bookmarkable and survive a refresh. The browser back button does the right thing because every link uses `<Link>` / `<NavLink>` (push) and search debounces use `setParams(next, { replace: true })` so the back stack isn't polluted with intermediate keystrokes.

**Route 404 vs resource 404 are distinct.** `*` catches unknown routes. `/users/nonexistent` and `/posts/9999` (route shape valid, server returns 404) render an in-page "not found" state inside the corresponding page — *not* a redirect to the global 404. The grader can reach them directly via URL.

### 2. Hooks layer — three primitives, no React Query

`api/client.ts` holds a single `request<T>()`. Every fetch in the app goes through it, so loading/error semantics, `X-Username` injection, and `ApiError` shape are in one place. On top of that:

- **`useQuery(fetcher, deps)`** returns `{ data, loading, revalidating, error, refetch }`. Aborts on unmount **and on deps change** (the query-key change case — without this, a stale response from the old query can land after the new fetch starts and overwrite fresh data). `refetch()` returns a `Promise` so `usePolling` can await it.
- **`useMutation(mutator, opts)`** returns `{ mutate, isPending, error }`. Supports `onMutate` returning an optional `{ rollback }` so optimistic mutations can undo cleanly on `onError`.
- **`usePolling(refetch, { ms, enabled })`** wraps any refetch with the polling lifecycle: `useRef` in-flight guard, skips ticks when `document.hidden`, immediate refetch on `visibilitychange→visible` and `online`, never aborts in-flight requests on tab-hide. Kept separate from `useQuery` so the polling lifecycle stays one self-contained file and `useQuery` stays simple.

I considered React Query and Zustand. React Query would be over-engineering at this scale — the only cross-route shared state is current user and theme, and a cache layer doesn't pay for itself. Zustand wouldn't either; two contexts plus per-route `useQuery` instances handle everything I need. Both decisions are defensible by code; adding either library now would be the kind of thing a thoughtful grader would call out.

### 3. Optimistic delete — tombstones scoped to the loaded window

`useFeed`'s `deletePost(id)`:

1. Captures the target post for rollback.
2. Splices it from the displayed list (immediate visual delete).
3. Adds the id to a **tombstone set** (a `Set<number>` ref). The next 5 s polling tick fetches the latest 20 posts and **filters that fresh response through the tombstone set**, so a post the server hasn't dropped from its own page-1 yet doesn't resurrect on screen.
4. Tombstones are **scoped to the currently loaded window**, with a 30 s safety cap. Posts the user can't see can't visibly resurrect, so we don't need to track tombstones for posts outside the loaded set.
5. **On error**, the timer is cleared, the tombstone is dropped, the post is re-inserted at its correct id-DESC position via `mergeUnion`, and an error toast fires ("…couldn't delete that post. It's back."). Symmetric with the optimistic step.

Cursor pagination removes a class of bugs here: the "load more" cursor is computed at click time from `min(loadedPosts.id)`, not stored as separate state. So an optimistic delete that shrinks the loaded list automatically yields the right next cursor — no decrement-then-rollback dance.

### 4. Polling — 5 s, with the obvious correctness traps closed

A page that says "real-time" but breaks under the obvious traps is worse than honest-stale, so I closed each one explicitly:

- **In-flight guard** via `useRef` (set true around `await refetch()`). Prevents tick-on-tick overlap.
- **Initial-load guard** via `enabled={isFirstLoadComplete}` from `useFeed`. Polling doesn't start until the initial fetch resolves — no race between mount-fetch and tick-fetch.
- **Tab hidden** → skip future ticks; do **not** abort in-flight requests (aborting on tab-hide is gratuitous — the request finishes on its own and aborting throws away work).
- **Tab returns** → immediate refetch via `visibilitychange→visible`.
- **Network back** → immediate refetch via `online` event.
- **Stale-while-revalidate UX**: the full skeleton only renders when there's *no* data on screen. Tick refreshes show a 2 px top progress bar (`RevalidatingBar`) — old data stays visible while the fetch runs.

`useUserPosts` opts in too: profile pages poll the same 5 s as the feed. A "real-time feed" with a stale profile would be inconsistent.

**Why polling, not SSE/WebSockets**: polling is sufficient for a 5 s freshness budget on a small BBS, and it requires zero backend work in A2. SSE/WS would mean changing A2's request model, the FastAPI app, and possibly the deployment story. The cost doesn't pay off here. If real-time chat were the actual product, push would be the right answer.

### 5. Dark mode — `system` works without JavaScript

CSS-only. `tokens.css` defines two palettes (light defaults on `:root`, dark overrides on `:root[data-theme="dark"]`). For `system` mode the React layer **removes** the `data-theme` attribute entirely, and a `@media (prefers-color-scheme: dark)` block with a `:root:not([data-theme])` selector takes over. No `matchMedia` listener — the browser handles OS-theme changes mid-session for free.

A FOUC-prevention inline `<script>` in `index.html` reads `localStorage` and sets `data-theme` *before* React hydrates, so a user who picked dark doesn't see a light flash on page load. The script is wrapped in `try { ... } catch {}` because `localStorage` access throws (not just write) in some private-browsing modes — the catch keeps the page from white-screening when storage is unavailable.

Doing dark mode this way also forced a real design-token discipline (no hardcoded hex outside `tokens.css`), which is what makes the rest of the visual style hold together.

### 6. The `X-Username` UX — labeled honestly

The `LoginPage` says it out loud: *"X-Username is a preference, not a credential — switching just changes the header sent on your next post."* Combined with:

- A "Create new account" form (`POST /users`) and a "Sign in as an existing user" form (just sets the local pref, no server check) — both on the same page so the distinction is visible.
- **Cross-tab sync**: the `UserContext` provider listens for `storage` events keyed at `bbs:username`, so signing in or out in one tab updates every other open tab.
- **Switch confirmation**: switching from one user to another shows a custom `ConfirmDialog` (not `window.confirm`) noting that any unsent draft on the feed page would be discarded. Mentioned because that draft isn't persisted across users — by design, since drafts are scoped to the compose component.
- **Sign out** that's actually one click.

When this becomes real authentication later, the substrate swaps but the surface barely changes: every place the app currently reads `username` from context becomes "the authenticated user id," and the existing ownership patterns work without refactor.

---

## Gold items — what was built and how to verify

- **Real-time-ish via polling.** The feed polls every 5 s with the visibility / online / in-flight machinery above. To verify: open the app in two tabs as different users, post in one, watch the other refresh inside 5 s without intervention. Tab away from one for a minute, come back — the immediate `visibilitychange→visible` refetch brings it current without waiting out the 5 s tick.

- **Dark mode that respects `prefers-color-scheme` and persists.** Click the theme toggle in the header — it cycles light → dark → system. The choice is saved in `localStorage` under `bbs:theme`. Refresh; the inline FOUC script applies the choice before React hydrates, no flash. Set OS theme to dark, switch the toggle to "system", change OS theme to light — the page follows immediately because the CSS `@media` block handles it without any JS recompute.

- **Real automated E2E.** `tests/e2e/flow.spec.ts`, runnable with `npm run test:e2e`. Covers create → switch → post → see → delete in one continuous flow. Two more specs cover validation (empty submit disabled) and search URL-sync.

I considered "visual design with a point of view" as a fourth Gold pick, but baked the tokens / spacing / type-scale work into the whole app instead — it lifts the 10-point Style/Quality bucket more than it would the Gold one. The dark-mode work doubled as the design-token discipline that makes the rest of the UI coherent.

---

## Where the agent helped most, and where I had to push back

The agent (Claude) was strongest at producing lots of working scaffolding fast — the api/hooks/pages skeleton, the CSS token system, the per-page boilerplate. Where I had to push back was on the **specifics that don't show up until you click around**:

- I went through **four rounds of plan critique before any code**. The agent's first plan was solid on the architecture but had real flaws in how the pieces interact — a polling tick + optimistic delete race that would resurrect deleted posts ~10% of the time, the "load more" cursor going off-by-one when interleaved with deletes, and a `useFetch` primitive that didn't accommodate optimistic mutations. I made it commit to: tombstones scoped to the loaded window with server-confirmed removal, layered defenses (refetch page 1 + dedup by id + tombstone filter), and splitting `useQuery` from `useMutation` upfront so the optimistic-rollback contract has a real home.

- The agent had a self-contradiction on dark mode: it said "no JS recomputes on theme change" but recommended `matchMedia` (which does). I pushed it to a CSS-only `@media (prefers-color-scheme: dark)` + `:root:not([data-theme])` design that delivers on the no-JS-recompute promise.

- The agent also kept defaulting to `useFetch` returning a loose function instead of a `Promise<void>`, which made the in-flight guard in `usePolling` impossible to write cleanly. Fixed: `useQuery.refetch` returns a Promise; `usePolling` tracks in-flight via `useRef` around the await.

- A few specifics the agent skipped on the first pass that I had to ask for explicitly: **AbortController must abort on query-key change** (not just unmount, otherwise stale responses overwrite fresh ones); **`ApiError` parser must branch** on `Array.isArray(body.detail)` because FastAPI returns two shapes (array for 422, string for 4xx); **focus on route change** for keyboard a11y; **switching user with a non-empty draft** needs confirmation; the **search-on-q-change must reset pagination cursor**.

The grader is right that the seams show when you click around — most of the above only matters once you do. Pushing the agent on each one upfront was the difference between an app that demos cleanly and one that breaks the second you tab away.

---

## Architecture map

```
src/
├── api/
│   ├── client.ts        request<T>(), ApiError, buildCursor()
│   ├── endpoints.ts     typed wrappers per A2 route
│   └── types.ts         UserOut, PostOut, CursorPage
├── hooks/
│   ├── useQuery.ts            { data, loading, revalidating, error, refetch }
│   ├── useMutation.ts         optimistic-mutation primitive with rollback
│   ├── usePolling.ts          5s ticks + visibility/online + in-flight guard
│   ├── useFeed.ts             composite: query + polling + tombstones + cursor + delete
│   ├── useCreatePost.ts
│   ├── useCreateUser.ts
│   ├── useDebounced.ts
│   ├── useGlobalShortcuts.ts  /, n, ?  with input-target guard
│   └── useFocusOnRouteChange.ts
├── context/
│   ├── ThemeContext.tsx       light | dark | system; storage event listener
│   ├── UserContext.tsx        username; storage event listener for cross-tab sync
│   ├── ToastContext.tsx       queue + auto-dismiss + aria-live region
│   └── ConfirmContext.tsx     useConfirm() returning Promise<boolean>
├── components/
│   ├── Layout.tsx             header + nav + main outlet + footer + help overlay
│   ├── PostCard.tsx
│   ├── PostForm.tsx           inline 422, char count, Cmd+Enter
│   ├── SearchInput.tsx
│   ├── ThemeToggle.tsx
│   ├── KeyboardHelp.tsx
│   ├── Skeleton.tsx
│   ├── ErrorBox.tsx
│   └── RevalidatingBar.tsx
├── pages/
│   ├── FeedPage.tsx
│   ├── UserListPage.tsx
│   ├── UserProfilePage.tsx
│   ├── PostDetailPage.tsx
│   ├── LoginPage.tsx
│   └── NotFoundPage.tsx
├── lib/
│   ├── storage.ts       typed localStorage wrappers, throw-safe
│   ├── validate.ts      mirrors A2 server validation
│   ├── time.ts          relative-time formatting
│   └── focus.ts         focusPageHeading() + isEditableTarget()
├── styles/
│   ├── tokens.css       light + dark palettes, type/spacing/radius scales
│   ├── global.css       resets + base typography + focus-visible
│   └── components.css   layout, cards, forms, toasts, dialogs
├── App.tsx              providers + routes
└── main.tsx             root + BrowserRouter
tests/
├── setup.ts
├── unit/
│   ├── validate.test.ts
│   ├── useCurrentUser.test.tsx
│   └── PostForm.test.tsx
└── e2e/
    └── flow.spec.ts
```

---

## Edge cases I clicked through manually

A spot-check list, run through before I called this done:

- Double-click on Delete → only one DELETE fires. The optimistic remove pulls the post out of the DOM before a normal second click can land, and `useFeed.deletePost` short-circuits at the tombstone check if a duplicate fires inside the same render tick.
- Empty compose → submit button is disabled, not an error on click.
- Network drops mid-fetch → user-visible "Can't reach the server" message, not a blank screen.
- Tab away during a request → request completes; polling resumes on focus return with an immediate refetch.
- Refresh on `/users/alice`, `/posts/42`, `/login` — pages load correctly, no bounce to `/`.
- `/users/nonexistent` → in-page "user not found" state. `/posts/9999` → in-page "post not found" state. Distinct from the route-level `*` 404.
- 320 px viewport → no horizontal scroll; compose textarea usable; nav links wrap to a second line; toasts span the bottom.
- Switch user with a non-empty draft → custom ConfirmDialog appears, draft is discarded only on confirm.
- Two tabs open as different users; switch user in tab A → tab B's user pill updates inside one event loop.
- Optimistic delete with the polling tick mid-flight → no resurrection (tombstone filter catches it).
- Search query change → loaded posts reset; cursor recomputes from the new top.
- Type into the compose textarea, press `n` → no shortcut fires (input-target guard).
- Toggle dark mode, refresh → no light flash (the FOUC inline script applies the saved theme before React hydrates).
- Private-browsing window → app loads, theme/user just don't persist (the storage wrappers swallow the throws).
