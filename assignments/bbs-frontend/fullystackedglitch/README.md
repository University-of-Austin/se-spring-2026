# BBS Frontend — fullystackedglitch (Assignment 4)

React + TypeScript + Vite frontend for the Assignment 2 BBS API.

## Tier targeted

**Gold** (silver requirements met, plus two of the four gold items: real-time updates + automated end-to-end tests).

- All six views, all eight A2 bronze endpoints wired up (plus `PATCH /users/{username}` for bio edits, which was A2 silver).
- Real routing via `react-router-dom`, every view has its own URL and survives refresh/back/forward.
- Optimistic delete on the feed with rollback on server failure.
- Numbered pagination on the feed (Prev / 1 2 … N / Next), URL-driven (`?page=`).
- Three keyboard shortcuts beyond Cmd+Enter, surfaced in a `?` overlay.
- **21 unit tests** (Vitest + RTL) across the API wrapper, compose form, pagination, the `useApi` hook, and the `localStorage` event channel.
- **6 Playwright tests** that drive a real Chromium: full create-user → post → see on feed → see on profile → refresh-keeps-identity → delete cycle, plus search-via-URL, validation, 404, sign-in autocomplete, and a two-tab polling test that proves a post made in tab A appears in tab B without a manual refresh. This covers the gold-tier "Real automated tests that prove the user flow" item.
- **Background polling** (`setInterval`, 5s, paused when the tab is hidden) on the feed. Covers the gold-tier "Real-time-ish updates" item; see design decision #7 for why polling over server-sent events.
- Accessibility basics: every input has a real label, every button is a real `<button>`, the modal is `role="dialog"`, the post list and pagination have `aria-current` / `aria-label` where it matters, and the sign-in dropdown is a full ARIA combobox.

## How to run

### 1. Backend (your A2)

```bash
cd assignments/bbs-webserver/fullystackedglitch
./venv/bin/uvicorn main:app --port 8000
```

### 2. Frontend

```bash
cd assignments/bbs-frontend/fullystackedglitch
npm install
npm run dev
```

Vite serves at `http://localhost:5173`.

### Environment

The backend URL is read from `VITE_API_BASE` and defaults to `http://localhost:8000`. To point at a deployed backend without code changes:

```bash
VITE_API_BASE=https://my-bbs.example.com npm run dev
```

See `.env.example`.

### Tests

```bash
npm run test       # unit, watch mode (Vitest + RTL)
npm run test:run   # unit, one-shot
npm run test:e2e   # Playwright against the dev server
```

`test:e2e` spins up the Vite dev server itself (`reuseExistingServer: true`, so it picks up the one you already have running), drives a headless Chromium, and exercises four flows in `tests/e2e/smoke.spec.ts`. The **A2 backend must be running on `:8000`** for e2e to pass, since the tests create real users and posts. First-time setup needs `npx playwright install chromium` to download the browser binary.

### Changes made to  Assignment 2 backend

- **Added `CORSMiddleware`** allowing `http://localhost:5173` (and `127.0.0.1:5173`) origins on all methods + headers. Without this the browser blocks every fetch from the dev server. Listed origins are deliberately narrow (production would read from an env var).
- That's the only A2 change. The endpoint shapes (`username`, `post_count`, `id`, `created_at`, `updated_at?`) survived the move to the browser intact.

## Design decisions

1. **One typed `api` module, generic `useApi` hook.** Every fetch goes through `src/lib/api.ts`, which throws a typed `ApiError` (with `.status` and `.detail`) on non-2xx. The wrapper digs the human-readable string out of FastAPI's two 422 shapes (`{ detail: "msg" }` and `{ detail: [{ msg }] }`) so views render `error.message` directly without having to re-parse. Views call those endpoints through `useApi(fetcher, key)`, which gives back `{ data, loading, error, refetch }` and aborts the in-flight request on unmount. The key-string design means I can rebuild a query (search, page, filter) without making `fn` part of the dependency array — that was a deliberate decision after Claude tried to put the fetcher in `useEffect`'s deps and trigger infinite loops.

2. **Optimistic delete with snapshot rollback.** The feed and profile views keep a *local* mirror of the server's posts (`localPosts`), seeded from `useApi.data` via effect. Clicking delete removes the row from `localPosts` immediately and fires the `DELETE` in the background. On failure, the prior list is restored from a closed-over snapshot and a banner explains why. I picked delete (not create) because the rollback is cheaper to reason about — no temp IDs, no reconciliation with the server's real `id` and `created_at`. (Create posts get an optimistic prepend on the feed too, but it's a "feels-fast" cheat, not a tracked optimistic update — the next refetch reconciles. I'd defend delete as the real silver-tier optimistic feature.)

3. **URL is the source of truth for the feed.** `?q=` and `?page=` live in the URL. The search input is a local state that pushes to the URL after 300ms idle — that way browser back/forward works as a search history and you can paste a `/?q=hello&page=3` link to a friend. Pagination doesn't try to fake a total count (the A2 API doesn't return one): it shows numbered pages up through the current one, plus the next page if `posts.length === pageSize`. False positives ("next" gives an empty page) are recoverable; false negatives (hiding next on a full page) are not.

4. **Identity is a `useSyncExternalStore` over `localStorage`.** The current `X-Username` lives in `localStorage` under one key, and `useCurrentUser()` is a thin `useSyncExternalStore` that subscribes to both the native `storage` event (other tabs) and a custom in-tab event (so the header re-renders the moment the signup form calls `setStoredUsername`). The "switch user" link in the header and the chip-grid in `/signup` both flow through the same setter. Calling out the obvious to the user: a banner in `/signup` explains that the header is a preference, not auth — anyone can pick any name, and the delete button is visible to everyone. That's the A2 contract, and pretending otherwise in the UI would be a lie.

5. **Loading / error scaffolding before success states.** Every view renders one of three branches (`LoadingBlock`, `ErrorBlock` with retry, or success). `useApi` flips `loading` true *before* the request starts so the user never sees a blank `data.map(...)` flash. The error block surfaces `error.message` verbatim — including FastAPI's 422 string — and offers a retry button that calls the hook's `refetch`. This was the lesson the assignment warned about: agents will happily `data.map(...)` with no guards, so the scaffolding lives in shared components that every view passes through.

6. **Sign-in is a real ARIA combobox over the user list.** The original `/signup` page had a chip grid of every existing user, which got unusable past ~30 users and didn't help anyone who knew their own name. The replacement is a combobox: type a few characters, the listbox shows the first 8 matches, arrow keys + Enter pick one, click-to-pick works via `onMouseDown` (so the input's blur doesn't unmount the dropdown before the click registers). Submitting a name that isn't in the list shows an inline error instead of the prior silent-failure mode where `localStorage` would happily store "ghost" and the next `POST /posts` would 404 with no UI feedback. The combobox is built with the ARIA pattern (`role="combobox"`, `aria-expanded`, `aria-controls`, `aria-activedescendant`, `role="listbox"` / `role="option"`) so screen readers and keyboard users get the same flow as mouse users. This is a nice-to-have.

7. **Real-time via polling, paused when the tab is hidden.** Every 5s the feed silently refetches the current page and merges results into `localPosts`. No loading spinner, no toast on a failed poll. I picked polling over server-sent events because the A2 API is a plain REST surface and the cost of adding an `/events` SSE endpoint plus a server-side broadcaster (FastAPI background task, in-memory subscriber map) is wildly out of proportion to the value at this app's scale. Polling is one `setInterval` and survives any backend topology. The visibility-state check stops the poll loop when the tab is backgrounded (no battery drain, no useless API load), and a `deletingIdsRef` filter prevents the poll from resurrecting a post that's mid-optimistic-delete. The two-tab Playwright test (`smoke.spec.ts:139`) is the proof: it creates two contexts, has tab A post, and asserts tab B sees it within one poll cycle.

8. **Three failure modes handled in the API wrapper.** Per the class principle: network (fetch throws, propagates), HTTP non-2xx (wrapped as `ApiError` with the parsed `detail.msg`), and bad JSON in a 2xx response (proxy-returned HTML, gateway error pages, etc., wrapped as `ApiError` with status + a useful message instead of leaking a raw `SyntaxError`). The unit tests cover all three.

9. **Mocking philosophy.** The class principle is "mocking is dangerous, mock only when necessary." Unit tests mock at the api-module boundary (compose form, pagination); testing UI behavior in isolation from the network is a legitimate use. The api wrapper itself is tested by mocking `globalThis.fetch` because that's the boundary we're testing. The real test of UI-against-network is the Playwright e2e suite, which mocks *nothing*: it boots a real dev server, drives a real browser, and talks to a real A2 backend. The two layers compose: unit tests prove components handle each possible API response correctly; e2e tests prove the components are wired to the right endpoints.

## Keyboard shortcuts

| Shortcut    | Action                             |
| ----------- | ---------------------------------- |
| `Cmd+Enter` | Submit a post (focused on compose) |
| `/`         | Focus the feed search box          |
| `?`         | Toggle the shortcuts overlay       |
| `Esc`       | Close the shortcuts overlay        |

The footer says "press `?` for shortcuts."

## Where my agent helped most and where I had to push back

Claude was very good at laying out the file structure, getting the CSS variable system going, and writing the typed `api.ts` wrapper. This is the boring scaffolding that would have taken my a few hours. It also wrote a clean first cut of the `Pagination` component once I had described "numbered pages but without a count endpoint, infer hasNext from page size." Claude also helped me with the tests and actually write the code for the stuff I pushed back on.

Where I had to push back: it tried to keep all the optimistic-delete state inside `useApi`'s `data` (mutating React Query-style), which would have re-fetched the page and made rollback problems. So I split into a mirror + snapshot pattern with a `useEffect` re-sync from `data`, which was Claude's recommendation when I asked for solution. It also tried to bake a `crypto.randomUUID()` temporary id into optimistic *creates* and reconcile on the response. We took that out so it looks more professional and has more functionality than the "looks done in 20 minutes" trap the assignment warns about. The other recurring thing was loading states: every view it generated rendered the success state first and the loading guard as a `<Skeleton />` that "would be added later."

After the silver-tier code was in place I added the Playwright e2e suite specifically because reading the assignment back I realized I hadn't actually clicked through anything, only verified the contract through `curl` and unit tests. Writing the Playwright spec is what shook out the seams: I use  `getByRole("article")` as a generic locator on the profile page, and it raced against the feed view's articles during the "Single Page Application" transition in the DOM. The fix was to scope locators inside `main` and select the HTML permalink by `href^="/posts/"` rather than by visible text. The test's first attempt matched the username because "e2e" contains a digit. The product itself didn't change, but the verification now exists, and `npm run test:e2e` is a one command reproduction for the full user flow.

## Gold tier items

Two of the four required:

1. **Real-time-ish updates via polling** (design decision #7). The feed background-refetches every 5s when the tab is visible. The Playwright spec `polling: a post made in tab A appears in tab B without a manual refresh` runs two browser contexts and confirms the propagation end-to-end.

2. **Automated tests that prove the user flow** (`tests/e2e/`). Six Playwright specs, runnable with `npm run test:e2e` while the A2 backend is on `:8000`. Covers create-user → switch-to-user → post → see-in-feed → delete (the literal flow the assignment specifies), plus the polling, search/URL-state, validation, 404, and combobox flows.

A third item is arguably here as a bonus: the sign-in **ARIA combobox** is a non-trivial invented UI feature with real state and interaction (design decision #6). The visual design has a deliberate dark palette, type/spacing scale via CSS variables, and reflows down to ~320px, which is might also be defensible as a fourth, but that is quite informal.
