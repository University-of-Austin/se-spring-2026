# BBS Frontend - Patrick Ramsay

A React + TypeScript + Vite client for the A2 BBS API.

## How to run

In one terminal, run the A2 backend (from `assignments/bbs-webserver/PpatrickR/`):

```bash
uvicorn main:app --port 8000
```

In a second terminal, from this directory:

```bash
npm install
npm run dev
```

Open the URL Vite prints (default `http://localhost:5173`). The frontend
reads the backend URL from `VITE_API_BASE` and defaults to
`http://localhost:8000`. To point at a different backend:

```bash
VITE_API_BASE=https://my-api.example.com npm run dev
```

## Tier targeted

**Silver.**

Bronze coverage:

- All six views implemented and reachable via real URLs.
- All eight A2 bronze endpoints wired up:
  `GET /posts`, `GET /posts/{id}`, `POST /posts`, `DELETE /posts/{id}`,
  `GET /users`, `GET /users/{username}`, `GET /users/{username}/posts`, `POST /users`.
- Every fetch shows a visible loading state, surfaces server errors (including
  the FastAPI `detail` field on 422s), and offers retry where it makes sense.
- Compose validates client-side (disabled when empty, char counter turning red
  past 500) and still surfaces 422 detail from the server inline.
- Current username persists across refresh via `localStorage`; sign-in/switch
  flow verifies the chosen username actually exists on the server before
  saving it, since A2 returns 404 from `POST /posts` for an unknown
  `X-Username`.

Silver additions:

- **Routing.** `react-router-dom` with real, bookmarkable URLs: `/`,
  `/compose`, `/users`, `/users/:username`, `/posts/:id`, `/signin`. The
  browser back button works. Routes that need an identity are gated by a
  `RequireUser` wrapper that redirects to `/signin` and preserves the
  intended destination via `location.state.from`.
- **Optimistic delete on the feed.** Each post that belongs to the current
  user gets a `delete` action on its row. Clicking it removes the post from
  the rendered list immediately; the actual `DELETE /posts/{id}` runs in the
  background. On failure the row is restored and an inline error toast shows
  the server's reason. Post-detail delete stays non-optimistic because once
  you've navigated away there's nowhere to roll back to.
- **Pagination.** Replaced the bronze prev/next with an infinite-scroll-lite
  "Load more" button. The button shows its loading state, and when the
  server returns fewer than `PAGE_SIZE` rows the label flips to "End of
  feed" and the button disables. Search is synced to the URL as `?q=` so a
  particular feed query is shareable.
- **Keyboard shortcuts.**
  `/` focuses the feed search box; `n` jumps to the compose page; Cmd/Ctrl+
  Enter posts the compose textarea while it's focused. All three are listed
  in a small footer line for discoverability.
- **Tests.** `npm test` runs a Vitest + React Testing Library suite under
  `tests/`. Three files, seven assertions total:
  - `ComposeView.test.tsx` covers the disabled-when-empty rule, the
    over-500 char-count + `aria-invalid` flip, and surfacing a mocked 422
    `detail` verbatim.
  - `FeedView.test.tsx` covers the optimistic-delete happy path *and* the
    rollback path: when `deletePost` rejects, the deleted post comes back
    and the inline error is visible.
  - `useCurrentUser.test.tsx` covers the localStorage round-trip, mount-time
    read of an existing value, and cross-tab sync via the `storage` event.
- **Accessibility.** Every input has a real `<label>` (via `htmlFor` or
  `.sr-only`). Buttons all carry visible text or an `aria-label`. Errors are
  in `role="alert"`, loading is in `role="status"`. Focus rings are explicit
  (`:focus-visible`) on every interactive element. The sign-in tabs are a
  real `role="tablist"` with `aria-selected`. Nothing is a `<div>` masquerading
  as a button.

## Test command

```bash
npm test          # one-shot, exits non-zero on failure (CI)
npm run test:watch # interactive watcher
```

## Changes I made to my A2 backend

- **CORS.** Added the FastAPI `CORSMiddleware` allowing `http://localhost:5173`
  so the browser will let the frontend read responses. Mentioned in the A2
  commit `76a630e`.
- **Ordering.** `GET /posts` now sorts by `created_at DESC, id DESC` so the
  newest post is first, since the Feed view depends on that. Same commit.

## Design decisions

- **Hooks layer instead of inline fetches.** `src/api/` is pure (no React, no
  `localStorage`); each view consumes it through a small `useFetch(fn, deps)`
  hook that returns `{ data, error, loading, reload }`. Optimistic delete in
  `FeedView` opts out and manages state directly because the rollback model
  doesn't fit a generic cache abstraction.
- **Routing as plain URLs, identity orthogonal.** Routes describe *content*:
  `/posts/42` is the post detail, regardless of who's logged in. Identity is
  a single `localStorage` key consumed by `useCurrentUser` and threaded into
  `POST`/`PATCH` calls via `X-Username`. There's no `/me` route; the header
  links the active username to their profile page like any other user.
  This is the right call because X-Username isn't real auth, so there's no
  reason to give the active user a privileged URL.
- **Optimistic-delete only, not optimistic-post.** I picked the cheaper
  rollback. Deletes are idempotent on the client (the row just disappears),
  the rollback is mechanical (re-insert the same object), and the failure
  modes are narrow (network blip, 403, 404). Optimistic-post would need a
  temporary ID, a way to thread it through Feed's pagination cursor, and a
  reconciliation step when the server-assigned ID arrives. For this app's
  scale it's not worth the complexity.
- **URL-synced search, in-memory pagination cursor.** `?q=` is in the URL so
  searches are shareable and survive refresh. The offset is *not* in the URL,
  since "Load more" is a session-local action, and putting `?offset=40` in the
  URL would mean a refresh skips the first 40 posts, which is the wrong
  default. If a user wants to "go back to the same point" they came from,
  the back button + URL `?q=` already covers the common case.
- **Stale-identity rejection at sign-in time.** A2 returns 404 from `POST
  /posts` if `X-Username` doesn't match a real user. Rather than surfacing
  that error only at post time, the Switch User flow does a `GET
  /users/{username}` first and refuses to store an identity that the server
  doesn't recognize. The Compose error path also detects 404 and points the
  user back to sign-in if their localStorage entry has gone stale (e.g.,
  the backend's `bbs.db` was wiped).

## Where my agent helped most and where I had to push back

The biggest catch was a "user not found" error on my first attempted post:
Claude's Sign-in view had a Switch User mode that accepted any regex-valid
username and wrote it straight to `localStorage` without asking the server,
so the first POST to my A2 backend 404'd. I had it add a
`GET /users/{username}` check before saving the identity and a more useful
404 message in Compose. The smaller pushback was visual: it had stuck a
"(press /)" hint inside the search placeholder which I made it remove.
