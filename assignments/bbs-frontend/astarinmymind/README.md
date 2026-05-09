# BBS Frontend (A4) — astarinmymind

A React frontend for [my A2 BBS API](../../bbs-webserver/astarinmymind/). UATX Software Engineering Spring 2026.

## How to run

```sh
# Backend (separate terminal, in your A2 dir)
uvicorn main:app --port 8000

# Frontend
npm install
npm run dev   # → http://localhost:5173
```

The frontend reads `VITE_API_BASE` (default `http://localhost:8000`).

### Changes I made to my A2 backend

Added `CORSMiddleware` to `main.py` so the Vite dev server (`localhost:5173`) can fetch from the API.

## Tier targeted

**Gold.** Picked options B (time-aware dark mode), C (Playwright e2e tests), D (visual design with a point of view).

## Design decisions

- All my backend calls go through one wrapper (`api/client.ts`) instead of inline `fetch()` calls in each hook, so URL, `X-Username` header, JSON parsing, and error handling all live in one place.
- The current username lives in a React Context (`UserContext`) backed by localStorage, so the header, compose form, and delete button can all read it directly instead of having `username` threaded through every component layer between.
- All routes share one `Layout` component (header + page slot via `<Outlet />`) instead of every page file repeating its own header — keeps the header consistent and the theme toggle / sign-in display only need to be wired in one place.
- On sign-in I verify the username exists via `GET /users/{name}` before claiming it, even though `X-Username` isn't real auth — better to catch a typo at sign-in than to let someone "sign in" as a nonexistent user and only discover it when their first post 404s.
- Four read hooks, one per GET endpoint (`usePosts`, `useUsers`, `useUser`, `usePost`) — each one owns its own fetch + loading/error state, so the pages just call it and render what comes back. Same return shape across all four means every consuming page looks identical.
- Pagination is infinite scroll inside a fixed-height post window (~3 posts visible at a time) — an `IntersectionObserver` watches a sentinel near the bottom of the scroll area and fetches the next page when it approaches view, instead of a "Load more" button.

## Tests

```sh
npx playwright test
```

*(arrives in Phase 5)*

## Where my agent helped most and where I pushed back

- Agent recommended going straight to gold architecture instead of iterating bronze → silver → gold, to avoid throwaway code from rewrites.
- Agent said to do step 1.2 (Tailwind color tokens) immediately because every component will use them.
- Agent explained `react-router-dom` is a library that maps URLs to React components, like FastAPI routes on the frontend.
- Agent suggested the Tailwind CSS IntelliSense VS Code extension (`bradlc.vscode-tailwindcss`) for inline color previews and class autocomplete.
- Agent suggested defining TypeScript types for `User` and `Post` so the compiler catches typos and shape mismatches before runtime.
- Agent confirmed defaulting to GET in my fetch wrapper is the universal convention — matches the HTTP spec, native `fetch`, axios, and every popular HTTP library.
- Agent introduced me to `Link`, `Outlet`, and `useNavigate` from react-router-dom — the SPA equivalents of `<a>`, a child-route placeholder slot, and programmatic URL changes.
- Agent first wrote a cancelled-flag race guard in `usePosts`; I pointed at Lecture 6.1's `AbortController` pattern and asked to use that instead, since it actually cancels the in-flight fetch and matches what we covered in class.
- Agent introduced me to `Promise.all` for firing parallel API calls — used in `useUser` to fetch the user info and their posts simultaneously instead of sequentially.

## Concepts I picked up along the way

### `Promise.all`

Fires multiple async operations at the same time and resolves once all complete. If any rejects, the whole thing rejects. Without it, you'd `await` the first call, then `await` the second sequentially — that's twice as slow because the second only starts after the first finishes.

```
sequential: [────fetch user────][────fetch posts────]   → 2x as long
parallel:   [────fetch user────]                       → bottleneck = slower one
            [────fetch posts───]
```

Two API calls is the threshold where `Promise.all` actually matters; any more and it matters more.

### Four-branch render (known 404 vs. generic error)

Pages that can fail in a *known* way ("this user doesn't exist") and a *generic* way (network died, server crashed) deserve different UI. That's why `UserProfilePage` and `PostDetailPage` have **four** render branches instead of three:

```tsx
if (loading) return <Spinner />
if (error instanceof ApiError && error.status === 404) return <NotFoundView />
if (error) return <ErrorMessage error={error} />
return <ContentView />
```

The `instanceof ApiError && status === 404` check is exactly why I threw a typed `ApiError` from `client.ts` instead of a plain `Error` — the `status` field lets pages branch on specific HTTP outcomes without parsing strings.

### Debouncing user input

Wraps a frequent event (typing, scrolling) so the actual handler only fires after a *quiet period*. Each new event cancels the previous schedule and starts a fresh countdown. Used in the search box so a fetch only goes out once typing pauses.

```
keystrokes:    h  a  i  ku                       (idle 300ms)
timers:        |  |  |  |
               ✕  ✕  ✕  ✕ ────[300ms]──▶ FIRES: setDebouncedSearch("haiku")
                          ↑ each prior timer cleared by next keystroke
```

Without it, typing "haiku" = 5 fetches (`?q=h`, `?q=ha`, …). With it, 1 fetch for `?q=haiku`. Saves backend load AND avoids race conditions where the `?q=h` response could arrive after the `?q=haiku` response and overwrite it.

Threshold: 300ms is the common default. Google uses ~150ms; sluggish forms 500ms+.
- Agent suggested a single `api/client.ts` wrapper around `fetch` so base URL, `X-Username` header, and error handling live in one place instead of being repeated at every call site.
