# BBS Frontend — Durp06

React + TypeScript + Vite frontend for the A2 BBS API.

**Tier targeted: Gold (all four gold sub-items).**

---

## 1. How to run

You need two processes — the A2 backend on `:8000` and this app on `:5173`.

### Backend (terminal 1)

```bash
cd ../bbs-webserver/Durp06
# install deps once (pip install -r requirements.txt) and activate your venv
python -m uvicorn main:app --port 8000
```

CORS middleware was added to A2 `main.py` — see §6 below.

### Frontend (terminal 2)

```bash
npm install
npm run dev
```

Open the URL Vite prints (default `http://localhost:5173`).

The backend URL comes from `VITE_API_BASE` (default `http://localhost:8000`):

```bash
# bash / zsh
VITE_API_BASE=http://localhost:8000 npm run dev
# PowerShell
$env:VITE_API_BASE = "http://localhost:8000"; npm run dev
```

### Tests (silver/gold)

```bash
npm run test        # Vitest: 9 unit tests (compose / feed / identity)
npm run test:e2e    # Playwright: full user flow against npm run dev + uvicorn
```

`npm run test:e2e` boots both the backend and the frontend itself via
Playwright's `webServer` config, so it really is one command. It assumes
`python` is on `PATH` and A2's deps are installed. First run only:

```bash
npx playwright install chromium
```

---

## 2. What the app does (the six required views)

| Route             | Page              | Endpoints used                                              |
| ----------------- | ----------------- | ----------------------------------------------------------- |
| `/`               | Feed              | `GET /posts` (`q`, `limit`, `offset`), `DELETE /posts/{id}` |
| `/compose`        | Compose           | `POST /posts` (with `X-Username`)                           |
| `/users`          | User list         | `GET /users`                                                |
| `/users/:user`    | User profile      | `GET /users/{u}`, `GET /users/{u}/posts`                    |
| `/posts/:id`      | Post detail       | `GET /posts/{id}`, `DELETE /posts/{id}`                     |
| `/signup`         | Sign-up / switch  | `POST /users` (and identity context switch)                 |

All eight A2 bronze endpoints are wired up.

---

## 3. Design decisions

1. **API calls live in a `src/api/` layer, not in components.** All `fetch`
   traffic goes through one wrapper (`client.ts`) that normalises errors
   into an `ApiError` class with `status` and `message`. FastAPI's 422
   `detail` shape (a list of `{loc, msg, type}` entries) is flattened into a
   readable message there so every page can just render `error.message`
   without re-deriving it. The endpoint helpers in `bbs.ts` are the only
   thing the rest of the app imports — pages and hooks never see a raw URL.

2. **Routing is real (`react-router-dom` v7), state is local, no global
   store.** Each resource has a tiny hook (`useFeed`, `useUser`, `usePost`,
   `useUsers`, `useUserPosts`) built on a shared `useResource` primitive
   that exposes `{ data, loading, error, refetch }`. I considered TanStack
   Query but it would be more dependency than this app earns — at five
   resources and one hot path (the feed), a hand-rolled hooks layer is
   easier to read and less to learn. Only the feed needs cross-page state,
   and it doesn't, because it remounts on navigation and re-fetches.

3. **Identity is a context that hydrates from `localStorage` synchronously
   in its `useState` initialiser.** No flash of "signed-out" content on
   refresh. `X-Username` is sent only with `POST /posts` (the one
   write endpoint that needs an author). Signing out just clears
   `localStorage` — there's no real session and the README on A2 already
   makes that contract clear ("not real auth"). The Sign-up page can also
   "switch existing user" without hitting the API, since users are
   identified by string only.

4. **Optimistic delete (silver), with rollback.** Clicking delete in the
   feed removes the row from the local list immediately, fires `DELETE
   /posts/{id}`, and on failure restores the row at its original index and
   pushes an error toast. Optimistic *create* is intentionally not done —
   the compose page is its own route and the user expects to be navigated
   back to the feed only after the server has acknowledged, so the latency
   is already hidden by the route transition.

5. **Polling, not push, for real-time-ish updates.** The feed polls
   `GET /posts` every 5 seconds. Reasons: (a) no backend changes needed
   — A2 doesn't speak SSE or websockets; (b) a 5s latency for "did
   someone else post" is fine for a BBS and indistinguishable from native
   in the common case; (c) the implementation is half a `useEffect` and
   easy to reason about. Polling pauses while the tab is hidden
   (`visibilitychange`) and skips its loading spinner so the feed doesn't
   flicker every five seconds. Background poll failures are swallowed —
   only the initial load surfaces errors, because nobody wants a toast
   storm during a flaky network.

6. **Theming via CSS custom properties and a `data-theme` attribute on
   `<html>`.** First load reads `localStorage('bbs:theme')`, then falls
   back to `prefers-color-scheme`. No FOUC — the toggle just flips the
   attribute and the variables cascade. The colour system is deliberately
   small: one accent, one surface, one bg, a text and muted-text, danger
   and success. Type uses a 1.250 modular scale anchored at 16px; spacing
   is on an 8px grid.

---

## 4. Where my agent helped most, and where I had to push back

The agent was great at scaffolding the boring shape — typed endpoint
helpers, the `useResource` hook, the shared CSS tokens, and the test
wiring. It was much faster than I would have been to bash out 200 lines
of CSS that all use the same five tokens. It also caught a real bug I
had introduced during scaffolding, where the feed hook was passing
`cursor: 'start'` to the backend on the initial load; my A2 cursor
decoder rejects that as base64-junk with a 422, which would have
silently broken the feed on the first render. I had to push back on it
in three places: (1) it wanted to put all the fetch calls inline in
the page components, and I made it consolidate them under `src/api/`
and `src/hooks/`; (2) its first pass at the optimistic delete
"removed-and-then-fetched-the-server's-view" within the same callback,
which races the poll loop and brings the row back — I made it commit
to a rollback model with an explicit `restore` mutator on the feed
hook instead; (3) every error path it generated had a generic "Error"
message until I made it surface `err.message` (the 422 `detail`) inline
and in toasts. The README question about which corners get cut is real
— "the row vanishes from the optimistic queue but a poll later resurrects
it" is exactly the kind of bug a happy-path-only build will ship.

---

## 5. Gold tier — what I did, in one sentence each

- **Real-time-ish updates.** `useFeed` polls `GET /posts` every 5 seconds,
  pauses when the tab is hidden, and merges new server posts in front of
  any still-pending optimistic ones (negative ids).
- **Dark mode.** `data-theme` on `<html>`, hydrates from `localStorage`
  then falls back to `prefers-color-scheme`, toggle button in the app
  shell (with `aria-label`) and `t` keyboard shortcut.
- **Playwright e2e.** `tests/e2e/flow.spec.ts` covers signup → switch user
  → post → see in feed → delete, boots both servers itself, run with
  `npm run test:e2e`.
- **Visual design POV.** Modular type scale (1.250 from 16px), 8px
  spacing grid, deliberate palette (burnt-orange accent on a warm-paper
  surface in light, amber-on-charcoal in dark), focus-visible everywhere,
  layout holds at 320px (header collapses into a two-row grid with a
  scrollable nav).

---

## 6. Changes I made to my A2 backend

Added `CORSMiddleware` to A2 `main.py` so the browser will let the
frontend on `localhost:5173` see responses from `localhost:8000`. Allows
only that one origin, all methods, all headers, no credentials. A2 tests
all still pass (`pytest` → 61 passed).

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

No other A2 changes were needed — the contract held up under a real
client.

---

## 7. Edge cases I specifically tested manually

- **Empty form submit:** post button is disabled until message is
  non-whitespace; can't be submitted by `Ctrl+Enter` either (the validity
  check runs in the submit handler).
- **Over the 500-char limit:** character counter turns red, button stays
  disabled, server-side rejection is shown inline if the client check is
  bypassed.
- **Double-click delete:** the row vanishes on the first click (optimistic
  removal), so the second click has no target. Button is also disabled
  via `deletingId` while in flight.
- **Tab away and back:** polling stops on `visibilitychange` (hidden) and
  fires once immediately on returning to visible, so the feed is fresh by
  the time the user looks at it again.
- **Backend gone for 30 seconds:** initial loads surface "Network error —
  is the backend running?" with a Try again button; polling failures are
  silent so the UI doesn't shake. When the backend comes back, the next
  poll succeeds and the UI returns to normal.
- **404s:** profile and post-detail pages render a dedicated "no such
  user/post" view when the API returns 404, not a generic error.
- **Mobile at 320px:** header collapses to two rows, nav scrolls
  horizontally, content has reduced padding. Tested in Chromium devtools.
