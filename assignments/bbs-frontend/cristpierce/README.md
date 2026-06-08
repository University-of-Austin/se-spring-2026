# BBS Frontend — Assignment 4

A React + TypeScript + Vite frontend for my Assignment 2 BBS API. You can log in by
username, read and search the feed, compose posts, click into profiles and post details,
react to posts, and switch users — all talking to the FastAPI backend I built in A2.

**Tier targeted: Gold** (all of bronze + silver, plus all four gold items).

---

## 1. How to run

You need two processes: my A2 backend and this frontend.

### Backend (A2 BBS API)

```bash
cd assignments/bbs-webserver/cristpierce
pip install -r requirements.txt          # fastapi, uvicorn, httpx  (+ sqlalchemy)
uvicorn main:app --port 8000
```

> The backend is included in this branch at `assignments/bbs-webserver/cristpierce/` so the
> whole stack is runnable from one checkout. `bbs.db` is created automatically on first run.

### Frontend (this app)

```bash
cd assignments/bbs-frontend/cristpierce
npm install
npm run dev          # Vite prints http://localhost:5173
```

Open the printed URL. The backend URL is read from **`VITE_API_BASE`** and defaults to
`http://localhost:8000`. To point at a different backend without touching code:

```bash
echo "VITE_API_BASE=https://my-api.example.com" > .env.local
```

### Backend change I made for this assignment (CORS)

The browser treats `localhost:5173` (frontend) and `localhost:8000` (API) as different
origins and blocks the page's JavaScript from reading API responses unless the server opts
in. I added `CORSMiddleware` to my A2 `main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],   # covers PATCH / DELETE
    allow_headers=["*"],   # lets the custom X-Username header through
)
```

I used an origin **regex** (any localhost/127.0.0.1 port) rather than a single hard-coded
origin so the dev server and the Playwright e2e server (port 5179) both work without edits.
This is the only change I made to my A2 backend.

---

## 2. Architecture (so I can actually narrate it)

The app is built in deliberate layers, smallest dependency first:

```
src/
  lib/        types.ts (the contract) · api.ts (the only fetch) · time.ts · mentions.tsx
  hooks/      useResource (loading/success/error machine) · useFeed · useMutation · useKeyboard
  context/    Identity (localStorage) · Theme (light/dark) · Toast
  components/ ui/ primitives (Button, Modal, StateView, Toaster…) + domain (PostCard, Composer…)
  pages/      Feed · Compose · Users · UserProfile · PostDetail · Auth · NotFound
  App.tsx     router only          main.tsx  providers + RouterProvider
```

**Which fetch lives where:** every network call is in `src/lib/api.ts` — nothing else in the
app calls `fetch`. Reads go through `useResource`/`useFeed`; writes through `useMutation` or
inline mutation handlers on the page that owns the relevant cache.

**What re-renders when I post a message:** `FeedPage.handlePost` builds an optimistic `Post`
with a temporary negative id and calls `feed.addOptimistic`, which dispatches into the
`useFeed` reducer — only the feed list re-renders, showing the post instantly in a "sending"
state. When the server's `201` returns, `feed.replaceOptimistic` swaps the temp post for the
real one (re-rendering that single card). On failure the temp post is removed and the
Composer shows the server's message inline.

**What happens if the backend goes away for 30 seconds:** `api.ts` wraps every request in an
`AbortController` timeout and normalizes connection failures into an `ApiError` with
`isNetwork: true`. `useResource`/`useFeed` move to the `error` state, and the page renders an
`ErrorView` ("Could not reach the server… Check CORS") with a **Try again** button — never a
blank screen. The feed's 5-second poll fails silently and self-heals when the server returns.

---

## 3. Design decisions

- **Hand-rolled data layer instead of React Query.** I wrote a ~90-line `useResource`
  state machine (`idle | loading | success | error`) and a `useFeed` reducer rather than
  pulling in a cache library. The reason is defensibility: I can point at exactly which hook
  owns which fetch, what aborts on unmount, and what re-renders on a post. The cost is manual
  cache invalidation, which at this scale is a few `setData`/dispatch calls and is itself a
  teachable trade-off. `StateView` makes the three states structurally unforgettable — its
  success branch is a render-prop that only receives defined data, so you *cannot* render a
  list without having handled loading and error first.

- **Optimistic updates on post, delete, and reactions, with rollback.** Posting prepends a
  temp post and reconciles on `201`; deleting removes the row immediately and restores it
  (re-sorted) on failure with a toast; reacting flips the highlight instantly. Every optimistic
  action captures the prior state so it can roll back. Dedup-by-id on every list merge means an
  optimistic post, its server echo, and a later poll of the same row never duplicate.

- **Real-time via delta-polling `/feed?since=`, not full refetch or websockets.** New posts
  are stashed and surfaced as a "N new posts" pill (so the feed never yanks your scroll
  position), polling only runs on the unfiltered first page while the tab is visible, and it
  sends the newest timestamp I hold so the server returns *only* new rows. Push (SSE/WS) would
  need backend work and our tolerance is ~5s, so polling the purpose-built endpoint fits.

- **Identity is a persisted preference, not auth — and the UI says so.** A2's `X-Username` is
  an honor-system header, so the `/login` page is framed as "choose who you post as" with no
  password, the username is stored in `localStorage` (and synced across tabs via the `storage`
  event), and a guest can read everything but is prompted to pick a username before posting.

- **Plain CSS with design tokens instead of a utility framework.** `tokens.css` defines a
  named type scale, spacing rhythm, color system, and shadows; light/dark are just two sets of
  semantic variables flipped by a `data-theme` attribute (applied pre-paint by a tiny inline
  script so dark-mode users never see a white flash). This reads as a deliberate system rather
  than utility-class soup, and every value is explainable.

---

## 4. Where my agent helped and where I had to push back

The agent was genuinely good at the boring-but-broad scaffolding — generating the typed API
client, the CSS-module design system, and twelve components fast — and at wiring the happy
path. Where I had to push back was exactly the seams this assignment warns about. Its first
`PostCard` wrapped the whole message in a `<Link>` to the post detail *and* rendered `@mentions`
as links inside it — nested `<a>` tags, which the browser flagged as a hydration error in the
console; I caught it with a real browser check and restructured so the timestamp is the
permalink and the message is plain text with inline mention links (siblings, not nested). I
also had to insist on the loading/error discipline up front — left alone it would render
`data.map(...)` with no guards — which is why `StateView` forces all three states by type. And
on reactions it cheerfully assumed a `GET /posts/{id}/reactions` that my A2 doesn't expose; I
worked around that real backend gap by persisting the current user's reaction locally and
treating a `409` as "already reacted" (documented below). Finally, the new
`eslint-plugin-react-hooks` v7 rules fought the latest-ref and data-fetching-effect patterns;
I fixed the ref ones properly and scope-disabled only the one advisory rule that flags a
documented React pattern.

---

## 5. Test commands

```bash
npm run test         # Vitest unit + React Testing Library component tests
npm run test:e2e     # Playwright end-to-end (starts the dev server itself)
npm run typecheck    # tsc on app + tests
npm run lint         # eslint
```

- **Unit / component (`npm run test`)** — 27 tests across the API error-normalizer (both
  FastAPI `detail` shapes), `useResource` state transitions, relative-time formatting,
  `@mention` parsing, and the Composer (disabled-when-empty, counter turns red past 500, server
  422 surfaced inline).
- **End-to-end (`npm run test:e2e`)** — runnable with one command, no backend needed: it serves
  the real frontend and emulates the A2 API at the network layer, then drives the full flow.

---

## 6. The four gold items

- **Real-time-ish updates.** The feed polls `GET /feed?since=<newest>` every 5s and surfaces
  new posts as a "N new posts" pill (see `useFeed`). README §3 explains why delta-polling beats
  push here.
- **An invented UI feature — reactions.** Emoji reactions on every post, backed by my A2
  `POST/DELETE /posts/{id}/reactions` endpoints, with optimistic toggling, switch-kind
  (remove-then-add, since the schema is one reaction per user/post), `409` reconciliation, and
  rollback. Because A2 exposes no `GET` for reactions, the client persists the active user's
  reaction in `localStorage` so "you reacted" survives a refresh — a documented workaround for
  a real backend gap.
- **Automated end-to-end test that proves the user flow.** `tests/e2e/flow.spec.ts` creates a
  user, switches to them, posts a message, sees it in the feed, reloads (identity persists), and
  deletes it — plus a search test. One command, deterministic.
- **Visual design with a point of view.** A modern-minimal system (neutral grays, one indigo
  accent, Inter, generous spacing) with a real type/spacing scale, first-class light **and**
  dark themes (respects `prefers-color-scheme`, persists, no flash), and a layout audited down
  to 320px.

### Keyboard shortcuts (beyond ⌘/Ctrl+Enter to post)

Press **`?`** anywhere (or the footer link) for the full list: `/` focuses search, `c` compose,
`h` feed, `u` users, `t` toggle theme, `Esc` closes dialogs.
