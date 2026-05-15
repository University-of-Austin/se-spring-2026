# A4: BBS Frontend (React + TypeScript + Vite)

**Tier targeted:** Gold (all 4 gold subitems)
**Location:** `assignments/bbs-frontend/Durp06/`
**Backend:** A2 API at `assignments/bbs-webserver/Durp06/` (sourced from
`bbs-webserver-Durp06` branch — needs to be re-materialized into the working
branch, plus CORS middleware added).

---

## 1. Scope summary

Build a React+TS+Vite app that consumes the A2 BBS API. All 6 required views,
all 8 bronze endpoints wired, loading/error/success states everywhere, identity
persisted via `localStorage`, real routing via `react-router-dom`, optimistic
updates, pagination, keyboard shortcuts, accessibility basics, dark mode with
`prefers-color-scheme`, polling-based real-time feed, Playwright e2e covering
the user flow, deliberate visual design.

## 2. Architecture (key decisions)

1. **API layer is isolated.** All `fetch` calls live in `src/api/client.ts`
   (low-level wrapper) and `src/api/bbs.ts` (typed endpoint methods). React
   components never `fetch` directly.
2. **Data layer is a hooks layer**, not a global store. Each resource has a
   custom hook (`useFeed`, `useUser`, `useUserPosts`, `usePost`, `useUsers`)
   returning `{ data, loading, error, refetch }`. Polling lives in `useFeed`
   via `setInterval`. No Redux / TanStack Query — keeps dependencies minimal
   and the data flow legible.
3. **Identity in a context.** `IdentityContext` exposes `{ username,
   setUsername }`, persists to `localStorage` on set, hydrates from
   `localStorage` on mount. One source of truth for "who am I".
4. **Routing is real.** `react-router-dom` v6 with routes: `/`, `/users`,
   `/users/:username`, `/posts/:id`, `/compose`, `/signup`. Back button works.
5. **Theming via CSS variables.** Light/dark theme toggled by `data-theme`
   attribute on `<html>`. Variables for color, type scale, spacing. Persists
   to `localStorage`, defaults to `prefers-color-scheme`.
6. **Optimistic updates on post create AND delete.** Both manipulate the local
   feed cache; on server error, rollback + toast.

## 3. Component map

```
src/
  main.tsx
  App.tsx                  # router shell + IdentityProvider + ThemeProvider
  api/
    client.ts              # fetch wrapper, error types, base URL
    bbs.ts                 # typed endpoints
    types.ts               # User, Post, etc.
  identity/
    IdentityContext.tsx
  theme/
    ThemeContext.tsx
  hooks/
    useFeed.ts             # GET /posts w/ polling + pagination + search
    useUser.ts             # GET /users/{username}
    useUserPosts.ts        # GET /users/{username}/posts
    usePost.ts             # GET /posts/{id}
    useUsers.ts            # GET /users
    useKeyboardShortcut.ts
  components/
    AppShell.tsx           # nav, identity widget, theme toggle, help (?)
    Loading.tsx
    ErrorMessage.tsx
    Toast.tsx
    PostCard.tsx
    UserChip.tsx
    HelpOverlay.tsx        # ? shortcut → modal
  pages/
    FeedPage.tsx
    ComposePage.tsx
    UsersPage.tsx
    UserProfilePage.tsx
    PostDetailPage.tsx
    SignupPage.tsx
    NotFoundPage.tsx
  styles/
    tokens.css             # CSS vars, light/dark
    base.css               # reset, layout, typography
```

## 4. Endpoint wiring (bronze checklist)

| # | A2 endpoint                       | Used in                                  |
|---|-----------------------------------|------------------------------------------|
| 1 | `POST /users`                     | `SignupPage`                             |
| 2 | `GET /users`                      | `UsersPage`                              |
| 3 | `GET /users/{username}`           | `UserProfilePage`                        |
| 4 | `GET /users/{username}/posts`     | `UserProfilePage`                        |
| 5 | `POST /posts`                     | `ComposePage` (optimistic)               |
| 6 | `GET /posts` (q, limit, cursor)   | `FeedPage` (polling + load more)         |
| 7 | `GET /posts/{id}`                 | `PostDetailPage`                         |
| 8 | `DELETE /posts/{id}`              | `PostDetailPage`, `FeedPage` (optimistic)|

## 5. Loading / error / success contract

Every hook returns `{ data: T | null, loading: boolean, error: string | null,
refetch: () => void }`. Pages render:

- `loading && !data` → `<Loading />`
- `error` → `<ErrorMessage message={error} onRetry={refetch} />`
- `data` → success view

On 422 the wrapper surfaces `detail` as the error message.

## 6. Forms / validation

- `ComposePage`: textarea + char count (red past 500). Submit disabled when
  empty. `Ctrl/Cmd+Enter` submits. Server 422 shown inline.
- `SignupPage`: username input. Regex `^[a-zA-Z0-9_]+$`, length 3–20. Submit
  disabled when invalid. Server 409 shown inline as "username taken".

## 7. Keyboard shortcuts

- `Ctrl/Cmd+Enter` — submit compose form (assignment requires this).
- `?` — toggle help overlay listing all shortcuts (the silver "at least one
  more shortcut beyond Cmd+Enter, surfaced visibly" requirement).
- `g f` — go to feed.
- `g u` — go to users.
- `n` — focus compose (only when on feed).

## 8. Accessibility (silver baseline)

Every `<input>` has a `<label htmlFor>`. Every button has visible text or
`aria-label`. Focus order is natural DOM order. No `<div onClick>` posing as
a button. Page is navigable via tab.

## 9. Gold — all four

1. **Real-time-ish (polling).** `useFeed` polls every 5s when the tab is
   visible. Cursor-stable: prepends new posts since last seen `id`. README
   explains why polling over SSE/WS (no backend changes needed, 5s latency is
   fine for a BBS, simpler).
2. **Dark mode.** `data-theme="dark"`/`"light"` on `<html>`. Hydrates from
   `localStorage("theme")` → falls back to `prefers-color-scheme`. Toggle in
   `AppShell` (sun/moon button, `aria-label`).
3. **Playwright e2e** in `tests/e2e/flow.spec.ts` covering: sign up → switch
   user → post message → see in feed → delete it. Runnable with `npm run
   test:e2e`. Spins up vite dev server via Playwright config.
4. **Visual design POV.** A coherent typescale (modular scale 1.250), 8px
   spacing grid, two accent colors (one light, one dark), generous line
   height, mobile-first responsive layout that holds up at 320px.

## 10. Testing (silver)

`tests/unit/` — Vitest + React Testing Library. At least:

1. `compose.test.tsx` — char count, disabled state, Ctrl+Enter submission.
2. `feed.test.tsx` — renders loading → renders posts → optimistic delete
   rolls back on error.
3. `identity.test.tsx` — `IdentityContext` persists username to localStorage
   and rehydrates.

Plus the gold Playwright spec.

## 11. Backend changes to A2 (CORS)

Add to A2 `main.py`:

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

Frontend README's "changes to A2" section calls this out.

## 12. Out of scope

- Real auth (X-Username header is the contract per A2 — explicitly noted).
- Image uploads, mentions, threads, reactions (none built in A2).
- Server-side rendering. Vite SPA only.
- A11y audit beyond the silver baseline (no screen-reader testing, no high-
  contrast theme audit).

## 13. Acceptance criteria (verifiable)

1. `cd assignments/bbs-frontend/Durp06 && npm install && npm run dev` boots
   the app against `VITE_API_BASE=http://localhost:8000`.
2. All 6 views present at the routes in §2.4.
3. All 8 bronze endpoints invoked from at least one view (§4 table).
4. Every page shows loading, then success or error.
5. Compose enforces 1–500 chars, Ctrl+Enter posts, 422 displayed inline.
6. Username persists across reload via `localStorage`.
7. URLs bookmarkable; back button works between pages.
8. Posting a message is optimistic; rollback on error.
9. `?` opens a help overlay listing shortcuts.
10. Dark mode toggle works, respects `prefers-color-scheme` on first load.
11. Feed auto-refreshes within ~5s of a new post elsewhere.
12. `npm run test` passes (Vitest, ≥3 tests).
13. `npm run test:e2e` passes (Playwright user flow).
14. README covers run/tier/4 design bullets/agent paragraph/test command.
15. App layout is usable at 320px width.
