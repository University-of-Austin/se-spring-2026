# thenetwork — BBS Frontend (Assignment 4) · Kyle Choy

> *A UATX Student Production. An online directory. Not a feed.*

A React frontend for the A2 BBS API. Visually homages 2004 thefacebook.com
(which started as a Harvard directory) reskinned in UATX brand DNA — the
shape says early-2000s college BBS, the paint says UATX. The thesis is
printed on every page: the original college social network was a directory
before it was a feed; this is the version that stops at the directory.

**Targeting Gold.** See `DESIGN.md` for the design system source of truth.

---

## 1. How to run

```bash
# Terminal 1 — A2 backend (on the bbs-webserver-kylehchoy branch)
cd assignments/bbs-webserver/kylehchoy
pip install -r requirements.txt
uvicorn main:app --port 8000

# Terminal 2 — this frontend
cd assignments/bbs-frontend/kylehchoy
npm install
npm run dev    # opens http://localhost:5173
```

The frontend reads the backend URL from `VITE_API_BASE`, defaulting to
`http://localhost:8000`. Override by copying `.env.example` to `.env.local`
and editing.

### Changes I made to my A2 backend

The browser blocks cross-origin requests by default — when JavaScript at
`localhost:5173` tries to fetch from `localhost:8000`, the two are
different origins and the response is hidden unless the server opts in.
Fix is one snippet in A2's `main.py`:

```python
# assignments/bbs-webserver/kylehchoy/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Location", "ETag"],
)
```

`expose_headers` matters: the frontend reads `Location` from `POST /posts`
(for redirects after compose) and `ETag` from `GET /posts/{id}` (for
conditional re-fetches). Without exposing them, those headers are present
on the wire but unreadable from JS.

No other backend changes.

## 2. Tier targeted

**Gold.** Three of the four gold criteria, done well rather than four flat:

1. **Visual design with a point of view** — the 2004-college-BBS-via-UATX
   thesis, executed under a documented design system (`DESIGN.md`). Variant
   C "The Almanac" from `/design-shotgun`, locked May 15, 2026.
2. **Real-time-ish updates** — TanStack Query `refetchInterval` polls
   `GET /posts` every 5s, visibility-paused when the tab is blurred. SSE
   was considered and rejected because A2 has no event bus; polling at
   class scale (~250 students) is fine and is documented in the
   architecture notes below.
3. **Invented UI: "Live Thread"** — `/posts/:id` becomes a Live Thread
   page combining `parent_id` reply trees + collapse/expand + optimistic
   reply insert + animated arrivals under poll + reactions with viewer
   state (`user_reactions` from A2 `GET /posts/{id}/reactions`). A single
   coherent interaction surface, not three bolt-ons.

(Playwright E2E was scoped as stretch — see "out of scope" below.)

## 3. Design decisions

(See `DESIGN.md` for the full design system. Architecture notes here.)

- **TanStack Query over hand-rolled hooks.** A class-scale BBS with
  polling + optimistic mutations + cache invalidation + dedupe is exactly
  the workload Query is built for. The hand-rolled version is ~200 LOC of
  `useEffect` choreography that Query handles in two props. Single new
  runtime dep, ~13KB gzipped.
- **Routing in URLs, not in conditional renders.** `react-router-dom` v7
  with `/`, `/users`, `/users/:username`, `/posts/:id`, `/signup`. Every
  view is bookmarkable, the browser back/forward button does the right
  thing, and the Live Thread page persists collapse state in
  `?collapse=12,17` so a refresh doesn't blow it away.
- **Optimistic updates for two mutations only.** Compose-post and
  reaction-toggle. Both use Query's `onMutate` → snapshot → `onError`
  rollback pattern; on success, invalidate the cached query. Negative IDs
  (`-Date.now()`) for temp posts to avoid collision with server IDs. Every
  other mutation (create user, delete post) is non-optimistic because the
  user benefit is not worth the rollback surface area.
- **Polling, not push, for real-time.** Visibility-aware
  `refetchInterval` (5s focused, paused blurred). SSE would require
  backend lifecycle changes I am intentionally not making — A2 is graded
  and frozen. Polling cost at ~250 users × 12 polls/min ≈ 3000 requests/min
  to a single SQLite-backed server, which is fine.
- **`X-Username` is preference, not auth.** A2 ships X-Username as a
  declarative identity header — no password, no token, anyone can claim
  any name. The UI surfaces this honestly: the current identity is a
  switchable pill in the header (`@kyle_choy [Switch]`), not a "you are
  logged in" badge. `localStorage` persists the choice across refresh.
- **One serif, one condensed sans, no third font.** Newsreader (free OFL
  analog of UATX's GT Super) for content; Antonio (free OFL analog of
  UATX's GT America Condensed) tracked-uppercase for chrome. A third font
  would muddy the editorial register.

## 4. Where my agent helped most and where I had to push back

*To finish in my own voice after I've kicked the tires myself.* Some
notes for memory while it's fresh:

- The biggest push-back was the "design" step. The agent's first instinct
  was to propose a design system from inferred context without asking me
  what I actually wanted. I called it out — the proposal was internally
  coherent but built on a memorable-thing I never approved. We
  re-scoped, did the UATX-vs-Harvard / Facebook-1.0-as-directory framing
  conversationally, then ran /design-shotgun against UATX's real brand
  assets and 2004 thefacebook.com archive screenshots. Variant C "The
  Almanac" came out of that.
- The shotgun's image-generation pipeline needed an OpenAI key I didn't
  have configured, so I pivoted the agent to hand-code four HTML
  mockups instead. That was actually better — real Newsreader/Antonio
  fonts loaded from the CDN, exact hex values, real 1px hairlines.
  Image generators garble small UI text anyway.
- On the React side, the agent wanted to inline fetch calls into
  components ("simpler, fewer files"). I pushed back: gold weighs code
  organization, and a hooks/api split is the canonical React 18 / Query
  v5 shape. The optimistic-update logic ended up in
  `src/hooks/useCreatePost.ts` and `useToggleReaction.ts` — both fully
  unit-testable, both used by ≥2 surfaces (Wall compose, reply
  composer, ReactionBar in both PostCard and ReplyCard).
- Loading + error states almost got cut for time. The assignment
  specifically calls out that "agents are bad at this by default" so I
  reused one States.tsx file across every fetch site rather than
  letting each page roll its own.

## 5. Tests + Gold-tier notes

```bash
npm test         # Vitest + RTL — 12 tests across 3 files
npm run test:watch
```

Test files (12 tests total):

1. `IdentityContext.test.tsx` (5) — covers the localStorage contract:
   `setUsername` persists, refresh-simulation restores, invalid usernames
   are rejected silently, `clear()` wipes, hook throws outside provider.
2. `ComposeBox.test.tsx` (4) — Join-CTA when no identity; locked
   `Dare to think. Dare to post.` placeholder; disabled-state at 0 and
   500+ chars; Cmd+Enter triggers submit.
3. `PostCard.test.tsx` (3) — renders body / time / username / open-thread
   href; ReactionBar present for real posts with correct count;
   optimistic (id < 0) posts show "posting…" and hide the bar.

**Gold-item one-liners:**
- **Visual POV:** Variant C "The Almanac" — UATX brand DNA (cream + antique
  gold + Newsreader serif + Antonio condensed sans) over 2004
  thefacebook.com bones (lowercase wordmark masthead, "my profile | my
  friends | my privacy | logout" nav, "Wall" / "Poke" / "is online"
  vocabulary). The thesis prints on every page: *An online directory. Not
  a feed.* See `DESIGN.md` and the locked variant at
  `~/.gstack/projects/SoftwareEngineering/designs/wall-feed-20260515/variant-C.html`.
- **Real-time polling:** `usePolling` wraps Query's `refetchInterval` with
  `document.visibilityState` so the feed and live-thread replies poll
  every 5s while the tab is visible and pause when it's hidden. The
  "Live" pulse dot in the masthead shows status. Two-tab test: user A
  posts, user B's feed/thread reflects within 5s.
- **Live Thread invented UI:** `/posts/:id` is a coherent thread surface
  combining `parent_id` reply tree (lazy-fetched per node on expand,
  capped at 3 visual depth levels), optimistic reply insertion against
  the same `useCreatePost` hook the Wall uses, polled arrivals with a
  250ms slide-in animation for newly-detected reply IDs only, and
  reactions inline on every node with `user_reactions` viewer state.

## 6. Keyboard shortcuts

- `/` focuses the Wall search input
- `?` opens the shortcut help overlay (also: a floating "?" hint bottom-right)
- `⌘/Ctrl + Enter` posts the compose / reply textarea
- `Esc` closes the shortcut overlay

## 7. Out of scope

- Adding new A2 endpoints. The contract is enough.
- Real auth (JWT/sessions). X-Username remains "preference" per A2 README.
- Server-sent events / websockets. Polling is sufficient.
- Multi-user presence ("alice is typing").
- A native mobile shell. Responsive web only.
- Playwright end-to-end spec (scoped as stretch; deferred unless Phases
  0–9 close ahead of schedule).
