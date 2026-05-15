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

*To be written after the build is complete.*

## 5. Tests + Gold-tier notes

```bash
npm test      # Vitest + RTL — runs the 3 component tests in tests/
```

Three Vitest + React Testing Library tests in `tests/components/`:

1. `ComposeBox` — disables submit when empty; shows live char count; turns
   red past 500; surfaces a server-side 422 detail inline.
2. `PostCard` — renders message, links username, fires `onDelete` only
   when current identity matches author.
3. `IdentityContext` — `setUsername` persists to `localStorage`;
   refresh-simulation restores it; invalid username (regex mismatch) is
   rejected.

**Gold-item one-liners:**
- **Visual POV:** Variant C "The Almanac" — UATX brand DNA over 2004 BBS
  bones; see `DESIGN.md` and the locked reference at
  `~/.gstack/projects/SoftwareEngineering/designs/wall-feed-20260515/variant-C.html`.
- **Real-time polling:** `usePolling` wraps Query's `refetchInterval` with
  `document.visibilityState`; "Live" pulse dot visible in the masthead.
- **Live Thread invented UI:** `/posts/:id` page combining thread trees,
  optimistic reply insert, polled arrival animations, and reactions with
  viewer state.

## 6. Out of scope

- Adding new A2 endpoints. The contract is enough.
- Real auth (JWT/sessions). X-Username remains "preference" per A2 README.
- Server-sent events / websockets. Polling is sufficient.
- Multi-user presence ("alice is typing").
- A native mobile shell. Responsive web only.
- Playwright end-to-end spec (scoped as stretch; deferred unless Phases
  0–9 close ahead of schedule).
