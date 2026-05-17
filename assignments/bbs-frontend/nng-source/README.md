# BBS Frontend

A React + TypeScript + Vite app sitting on top of the A2 backend.

## How to run

Two processes — one for the API, one for the UI.

**Terminal 1 — A2 backend** (from repo root):

```bash
cd assignments/bbs-webserver/nng-source
# activate your A2 venv first
uvicorn main:app --port 8000
```

**Terminal 2 — A4 frontend** (this directory):

```bash
npm install
npm run dev
```

Vite prints a URL (usually `http://localhost:5173`). Open it.

The frontend reads `VITE_API_BASE` from the environment (defaulting to `http://localhost:8000`). Override via `.env.local` if your backend lives elsewhere.

### Running the tests

```bash
npm test
npm run test:watch
```

## Changes I made to my A2 backend

1. **CORS.** My A2 had no CORS configuration, so the browser blocked every cross-origin fetch from `localhost:5173`. Added `CORSMiddleware` to `main.py` with `allow_origins=["http://localhost:5173"]`, methods `*`, headers `*`, credentials `True`. Lives on a separate branch (`cors-fix-nng-source`) so the fix doesn't get tangled into this PR.

2. **Nothing else.** Every endpoint the spec wires up was already present from my silver A2, including `PATCH /users/:username` for bio and `DELETE /posts/:id`.

The spec describes a simpler `X-Username`-header-as-auth model. My A2 went past that: writes need both a session token (`Authorization: Bearer ...`) AND `X-Username`, with real password-based signup/login. I kept that model. The frontend's sign-up form takes a password, calls `POST /login` immediately after to grab a token, and stores `{ username, token }` together in `localStorage`.

## Architecture decisions

### Routing

`react-router-dom` (`createBrowserRouter`) drives every view. URLs are real and bookmarkable:

| Route               | Page          |
| ------------------- | ------------- |
| `/`                 | Feed (with `?q=` for search) |
| `/users`            | User list     |
| `/users/:username`  | Profile + their posts + bio editor (own profile) |
| `/posts/:id`        | Single post + delete |
| `/login`            | Log in        |
| `/signup`           | Create account |

Refresh and back-button work as expected.

### State / cache

I deliberately did NOT pull in TanStack Query or Redux. The feed has its own polling loop; every other page uses a tiny `useAsync` hook (`src/hooks/useAsync.ts`) that returns `{ data, loading, error, reload, setData }` and guards stale-state writes with a generation counter. The whole hook is ~40 lines. The lecture material covered `useEffect`-based fetching; adding a query library for a 6-route app would have been heavier than the problem.

### Identity persistence

`{ username, token }` go into `localStorage` under `bbs.username` and `bbs.token`. On first mount `AuthProvider` reads them; on every change it writes them. Logout clears both and (best-effort) calls `POST /logout` to invalidate the server-side session.

### Loading / error / success — always three states

`Spinner` and `ErrorBox` are reused everywhere a fetch is in flight. The pattern in every page is `if (loading) → if (error) → if (notFound) → render`. A blank screen never appears. `ErrorBox` includes a retry button that re-fires the loader. 422 detail from FastAPI is normalized to a string by `extractDetail` in `api.ts` so it surfaces inline rather than getting stringified into `[object Object]`.

### Optimistic updates

`POST /posts` is optimistic. `Compose` synthesizes a placeholder with a negative id, hands it to the feed via `onOptimisticAdd`, then swaps it for the real post via `onConfirm` or removes it via `onRollback` on failure (restoring the draft so the user doesn't lose their text). `DELETE /posts/:id` is also optimistic — snapshot the array, splice the row, restore on failure.

`PATCH /users/:username` (the bio editor) is intentionally NOT optimistic; it's a settings-style write where seeing the spinner is useful feedback.

### Pagination

Offset-based "load more" against `GET /posts?limit=25&offset=N`. The button hides when the server returns fewer than `PAGE_SIZE` rows. I picked offset over cursor because my A2 already supports it; switching to cursor would have meant changing both ends.

## Gold features

### 1. Real-time-ish updates via polling

While the feed is open and the tab is foregrounded, a `setInterval` fires every 5 seconds and refetches the head of the feed. New post ids (ones we haven't seen) get prepended and a small **"N new posts above"** pill appears, so a user scrolled down still sees motion. Polling pauses when `document.hidden` is true so backgrounded tabs don't churn requests.

I picked polling over SSE/WebSockets because:
- My A2 is a vanilla FastAPI app — no event loop wiring, no long-poll endpoint, no broadcasting.
- BBS traffic is conversational, not chat-realtime. 5 seconds is plenty.
- It's ~30 lines of frontend code with no server-side changes; SSE would have been a backend PR plus an EventSource consumer plus reconnect logic.

The polling loop is careful: a reentrancy guard prevents stacking when a request hangs longer than the interval, and the merge logic drops any optimistic placeholder once the real post arrives so a user posting and polling at the same time doesn't end up with a duplicate.

### 2. Visual design with a point of view

Single CSS file in `src/index.css` driven entirely off CSS custom properties — type scale, spacing scale, color tokens, two themes via `prefers-color-scheme`. The dark theme leans terminal-y (cyan accents, monospace body) because it's a BBS. The light theme stays readable; both share the same accent. One responsive breakpoint at 540px collapses the header nav and the search form.

I avoided Tailwind / CSS-in-JS / a component library deliberately. The whole stylesheet is one file, greppable, and short enough to skim end-to-end.

## Keyboard

| Key                         | Effect |
| --------------------------- | ------ |
| `/`                         | Focus the search box on the feed |
| `n`                         | Focus the compose textarea |
| `Cmd`/`Ctrl` + `Enter`      | Post message (while in compose) |
| `Tab`                       | Nav → search → compose → posts in document order |

Listed in the footer so they're discoverable without poking around.

## Accessibility

- Every form input has a real `<label>` tied via `htmlFor`/`id`. Where the label is visually redundant (search, compose), it's still present as `.visually-hidden`.
- Every button has visible text or an `aria-label` (e.g., `Delete post 42`).
- The spinner uses `role="status" aria-live="polite"`. The error box uses `role="alert"`.
- `aria-invalid` flips on inputs when client-side validation fails so screen readers announce the state.
- All interactive elements are real `<button>` / `<a>` / `<input>` — no `div onclick`.
- Focus rings are visible (2px accent outline) and not removed.

## Project structure

```
src/
  api.ts              # fetch wrapper, typed endpoint functions
  auth.tsx            # AuthProvider + useAuth + localStorage persistence
  types.ts            # API response types + ApiError
  main.tsx            # router + provider wiring
  hooks/
    useAsync.ts       # generic data-loading hook with reload + setData
  components/
    Compose.tsx       # textarea, char counter, optimistic submit
    ErrorBox.tsx
    Layout.tsx        # nav + outlet + global keyboard shortcuts
    PostCard.tsx
    Spinner.tsx
  pages/
    Feed.tsx          # search, pagination, optimistic posts, polling
    Login.tsx
    PostDetail.tsx
    Profile.tsx
    Signup.tsx
    Users.tsx

tests/
  setup.ts            # @testing-library/jest-dom + auto-cleanup
  Compose.test.tsx
  PostCard.test.tsx
  auth.test.tsx
```

15 tests pass via `npm test`.
