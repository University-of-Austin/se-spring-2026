# BBS Frontend — Almar-T

Gold tier submission for Assignment 4. A React + TypeScript + Vite frontend
that talks to my A2 FastAPI backend. Six views, real routing, optimistic
posting and deletion, polling-based real-time updates, a custom reactions
UI built on top of my A2 gold endpoints, and a designed visual identity
with dark mode.

---

## 1. How to run

You need **two processes** during development — the A2 backend on port
8000 and this frontend on port 5173.

### Terminal 1 — backend (A2)

```bash
cd assignments/bbs-webserver/Almar-T
pip install -r requirements.txt
uvicorn main:app --port 8000
```

The backend must be running the version of `main.py` on the
`bbs-webserver-Almar-T` branch with the **CORS middleware enabled** —
that's the only change A4 required of A2. See §"Changes I made to my A2
backend" below. Without CORS, the browser will refuse to expose the
response to JS and every fetch will fail with a network error in the
DevTools console.

### Terminal 2 — frontend (A4)

```bash
cd assignments/bbs-frontend/Almar-T
npm install
npm run dev
```

Vite serves on <http://localhost:5173>. Open that.

### Pointing at a different backend

The base URL is read from `VITE_API_BASE`, defaulting to
`http://localhost:8000`. To use a deployed backend instead:

```bash
VITE_API_BASE=https://my-bbs.example.com npm run dev
```

It's an `import.meta.env.VITE_API_BASE` lookup in `src/api/client.ts` —
no code changes needed to swap origins.

### Running the test suites

```bash
npm test                 # vitest — 4 files, 20 component/hook/client tests
npm run test:e2e         # playwright — 3 specs, real browser, real backend
```

The Playwright config starts the Vite dev server itself (`webServer` block),
but the backend still has to be running on :8000 first. First run, do
`npm run test:e2e:install` to grab the chromium binary.

---

## 2. Tier targeted

**Gold.** Bronze + silver + three of the four gold options:

- All six views (feed, compose, user list, profile, post detail, sign-in)
  implemented as real routes, all eight bronze A2 endpoints wired up,
  loading + error + 422 inline-validation states everywhere.
- Silver: `react-router-dom`, optimistic compose AND optimistic delete,
  load-more pagination, two keyboard shortcuts beyond ⌘+Enter
  (`g f` / `g u` for nav, `?` for a help overlay), basic accessibility
  (labels, aria-labels, focus styles, keyboard reachability), vitest +
  React Testing Library tests on three files.
- Gold: polling-based real-time, a custom reactions UI built on my A2's
  reactions endpoints, a Playwright e2e spec that exercises the full
  flow against a real backend, and a deliberate visual identity
  (typography pairing, color palette, dark mode, mobile responsiveness).

See §6 for a sentence on each gold item.

---

## 3. Design decisions

### Single `apiFetch` wrapper, one thin file per resource

Every fetch in the app goes through `src/api/client.ts:apiFetch`. That
one function owns the URL prefix, 204-handling, error parsing, and a
network-failure fallback that throws an `ApiError(0, …)` so the
"backend is down" case has the same shape as every other failure. Each
resource (`posts.ts`, `users.ts`, `reactions.ts`) is a thin module of
typed wrappers — `listPosts(...)`, `getUser(...)` — over `apiFetch`.
The rule is: components never call `fetch` directly; pages call hooks
which call resource modules which call `apiFetch`. So when I added
optimistic updates, I changed only the pages — the network layer
didn't move at all. And when I needed to surface FastAPI's 422 detail
arrays (those `[{loc, msg, type}]` shapes) as a single human-readable
string, I changed one function. The unit-tested error path in
`tests/api-client.test.ts` checks both the 422 array shape and the
`detail: string` shape — same code path, two cases.

### `useFetch` returns `setData`, so optimistic updates are a page-level
concern, not a global cache

I considered pulling in React Query for caching. I didn't — for ~8
endpoints with no need to deduplicate or share data across far-apart
components, it would be more ceremony than it's worth. Instead, the
generic `useFetch<T>` hook exposes a `setData(updater)` escape hatch
that lets a page mutate its own cached result. The optimistic-compose
flow in `FeedPage` is concretely: insert a placeholder post with a
negative temp ID at the top of state → call `createPost` → on success
replace the temp with the saved post by ID → on failure remove the temp
and rethrow so the `Composer` shows the server's `detail` inline.
Optimistic delete is the symmetric thing: filter the post out
immediately, remember its index, restore it at that index if the API
rejects. Both paths share the same property: **the UI never lies for
long**. If the server says no, the rollback puts the world back to a
state consistent with what the server actually believes.

The trade-off this *doesn't* solve is concurrent state across multiple
open tabs / multiple components viewing the same post. If you delete a
post on the feed page and then navigate to that post's detail URL, the
detail page will re-fetch and 404 correctly — so the staleness window
is bounded by the next navigation. For a real product I'd care more;
for an A4 BBS I'd rather keep the cache local and predictable.

### Polling for real-time, not WebSockets — and only the feed polls

Real-time updates use `setInterval(refetchFirstPage, 5000)` on the feed
page only. Polling is the right call here for three reasons. (1) The
backend is a plain FastAPI app with no WebSocket route — adding
push-style updates would mean a real backend change, not just a CORS
middleware bolt-on. (2) Only the feed needs near-live updates; the
profile and post-detail pages are inherently single-fetch-per-mount
views. (3) Polling fails gracefully: dropped requests, intermittent
network, an unreachable backend — the UI just keeps showing the last
good state and silently retries. There are three real refinements over
the naive version: polling pauses when the tab isn't visible
(`document.visibilityState`), polled refreshes don't flash the
loading state (they only swap data when the data actually changed),
and new posts are *merged* into the existing list rather than
replacing it, so users who scrolled or who have unsaved typing in the
composer aren't yanked out of context. When new posts arrive a banner
appears: "*N new posts — scroll to top*" — discoverable, not
disruptive.

### CSS modules + design tokens, not Tailwind

Styling uses `*.module.css` files for component-scoped class names plus
a single `tokens.css` defining the color palette, type scale (1.125
modular ratio), spacing scale (4px base), and shadow ramp. Tailwind
would have been faster to *write*, but two things tipped me the other
way: (1) the assignment grades visual design as one of the gold
options, and a custom tokens file is much easier to defend in a README
than "I used these Tailwind classes"; (2) component CSS sits next to
the component file with the same name, which makes refactors easier
than chasing `className`s through JSX. Dark mode is opt-in via a
header toggle that writes a `data-theme` attribute on `<html>`, but
falls back to `prefers-color-scheme` if the user hasn't set a
preference. The whole theming machinery is ~30 lines of CSS variables
plus one hook (`useTheme`).

### `X-Username` is identification, not authentication — and the UI says so

The A2 backend uses `X-Username` as a header on `POST /posts` to mark
authorship, but anyone can send any value. The frontend has to be
honest about this. Three places where it shows up:

1. The sign-in page literally says, in muted text below the form,
   *"BBS uses your username as your identity. This is **not real
   authentication** — it's a preference saved in your browser's
   localStorage, sent with each post in the `X-Username` header.
   Anyone can claim any name."*
2. The post card shows a `⚠ not your post` indicator next to the
   Delete button when the signed-in user doesn't match the post's
   author — making the "no auth" reality visible at the moment it
   matters. Deletion still works (the backend doesn't check), but the
   user is told what they're doing.
3. The `X-Username` header is only attached to `POST /posts` —
   never to GETs and never to DELETEs — because that's where A2
   currently uses it. Adding it everywhere would be cargo-cult; the
   day real auth lands, the change site is `src/api/posts.ts:createPost`,
   nothing else.

### Routing with `react-router-dom` v6, lazy-loaded pages

`/`, `/users`, `/users/:username`, `/posts/:id`, `/sign-in`, and a
catch-all `*` → 404 page. Each page is a `React.lazy(() => import(...))`
so the initial bundle is 175KB but each route adds only its own slice
(~2-5KB per page). All routes are bookmarkable, the back button does
the right thing, refreshing on any URL works.

---

## 4. Changes I made to my A2 backend

**One.** I added `CORSMiddleware` to `main.py`. Browsers treat
`localhost:5173` (Vite) and `localhost:8000` (FastAPI) as different
origins; without an explicit CORS opt-in, the browser refuses to let JS
read the response from a cross-origin `fetch()`. The fix is the
standard one from the FastAPI docs:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`allow_origins=["*"]` is the right call here only because we don't use
cookies — the wildcard CORS rule prevents the browser from sending
credentials, but my app authenticates with a header (`X-Username`),
not a cookie, so the wildcard doesn't cost me anything. In a real
production setup I'd pin it to the deployed frontend's origin.

This change was committed separately on the `bbs-webserver-Almar-T`
branch (commit `18aec54`); see the diff there. No other A2 code was
touched.

---

## 5. Where Claude helped most, and where I had to push back

The first-pass scaffolding — types, the `apiFetch` wrapper, route
setup, basic component shells — Claude was great at; that's the
"happy path code an agent ships in 20 minutes" the assignment warns
about. What it would NOT have done without prompting was the
optimistic delete's index-aware rollback (its first cut was a "filter
out then refetch" approach that would flash the entry back at the
bottom of the list); the polling pause when the tab is hidden (it
defaulted to "just `setInterval`" until I asked what happens when the
user is in another tab for 8 hours); the merge-vs-replace behaviour
on polled feed updates (its first version replaced the whole list and
threw away unsaved typing in the composer); and the `X-Username`
"not real auth" warning UI, which I had to push for explicitly. It
also hit a real bug I almost missed: each call to `useCurrentUser`
was creating an independent piece of `useState`, so signing in
updated `SignInPage` but the header didn't see the change because
storage events only fire in *other* tabs, not the writer's tab —
caught by the Playwright spec failing on "header chip not visible
after sign-in", fixed with a tiny module-level pub/sub. The lesson I'm
taking away is that an agent will produce code that works the first
time you click through it; everything that goes wrong on the second
click is what you have to push it on, by name, one case at a time.

---

## 6. Gold features — one sentence each

- **Real-time polling.** Feed page refetches the first page every 5s
  when the tab is visible, merges new posts at the top, surfaces a
  *"N new posts — scroll to top"* banner instead of disrupting the
  view. See §3 for the trade-offs against WebSockets.
- **Custom UI feature — reactions.** A reactions bar under every post
  with a popover emoji picker, click-to-toggle behaviour, and a count
  pill highlighted differently for your own reactions; built on my A2
  gold `POST/GET/DELETE /posts/{id}/reactions` endpoints, with no
  backend changes needed. Reaction fetches fail silently because they're
  non-essential — the rest of the card stays usable if reactions error.
- **Visual design with a POV.** Hand-built design tokens (1.125 modular
  type scale, 4px spacing base, terra-cotta accent on warm cream),
  monospace headers + sans body, dark mode toggle that respects
  `prefers-color-scheme` when unset, and the layout is responsive down
  to 320px (the header collapses the brand name; the search input goes
  full-width on mobile; the toast stack repositions). One clear visual
  identity, defended by being one file (`tokens.css`).
- **Real automated e2e tests.** A Playwright spec at
  `tests/e2e/full-flow.spec.ts` that creates a user, posts a message,
  reloads the page (proving localStorage persistence), deletes the
  post, and asserts on the success toast — all against a real running
  backend and a real Vite dev server. Plus two smaller specs covering
  the 404 view and the 500-char client-side validation. Runnable with
  `npm run test:e2e`.

---

## 7. File map

```
src/
  api/            apiFetch + one resource file per endpoint group
  hooks/          useFetch, useCurrentUser, useToast, useTheme,
                  useKeyboardShortcut
  components/     Layout, Header, Composer, PostCard, ReactionBar,
                  Pagination, HelpOverlay, ErrorBanner, LoadingDots,
                  Timestamp, UserBadge — each with its own .module.css
  pages/          FeedPage, UsersPage, UserProfilePage, PostDetailPage,
                  SignInPage, NotFoundPage
  styles/         tokens.css + global.css
tests/
  *.test.tsx      vitest unit tests for Composer, PostCard,
                  useCurrentUser, and api/client
  e2e/            Playwright specs (run separately)
  setup.ts        vitest setup — jest-dom matchers + cleanup
```
