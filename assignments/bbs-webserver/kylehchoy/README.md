# BBS Webserver (Assignment 2) — Kyle Choy

FastAPI wrapper around a SQLite-backed bulletin board. Targets **Gold**: the
eight bronze endpoints, silver bio/post_count/PATCH/`?username=`, and the
Gold cursor envelope `{"posts": [...], "next_cursor": "..."}` on
`GET /posts`. Additional Gold-scope features (FTS5 search with bm25 and
snippets, weak ETags with 304, Stripe-style `Idempotency-Key`, reactions,
threaded replies, popularity ranking) built on the same three-layer base.

---

## 1. How to run

```bash
cd assignments/bbs-webserver/kylehchoy
pip install -r requirements.txt
uvicorn main:app --port 8000
```

In a second shell:

```bash
python verify_api.py     # expect: 158 passed, 0 failed
```

`bbs.db` is created on first start. Delete it to reset. The verifier uses a
random per-run suffix so it does not need a clean DB.

---

## 2. Tier targeted

**Gold.** Rolled up per layer:

- **Bronze:** 8 required endpoints, Pydantic validation, `X-Username` identity.
- **Silver:** `bio` + `post_count` on users, `updated_at` on posts,
  `PATCH /users/{username}`, `PATCH /posts/{id}` (author-only),
  `?username=` filter on `GET /posts`.
- **Gold features:**
  - **Cursor pagination** on `GET /posts` — envelope
    `{"posts": [...], "next_cursor": "..."}` per the spec.
    `next_cursor` is `null` on the last page and on non-cursor paths.
    `?cursor=` with `?offset > 0` → 422.
  - **FTS5 search** on `?q=` with bm25 ranking, `snippet()` highlighting,
    and AFTER INSERT/UPDATE/DELETE triggers keeping the index in sync.
  - **Weak ETags** on `GET /posts/{id}` and `PATCH /posts/{id}`;
    `If-None-Match` → 304.
  - **`Idempotency-Key`** on `POST /posts`, exactly-once under
    concurrency (two-phase claim in one transaction).
  - **`Location`** headers on `POST /users` and `POST /posts`.
  - **Bounded pagination** (`limit` 1–200, `offset ≥ 0`) on every list
    endpoint.
  - **Reactions:** `PUT/DELETE /posts/{id}/reactions/{kind}`,
    `GET /posts/{id}/reactions` with per-kind counts and viewer-scoped
    `user_reactions`. `PRIMARY KEY (user_id, post_id, kind)` carries
    idempotency; `ON DELETE CASCADE` sweeps on post delete.
  - **Embedded `reaction_counts`** on every post response, zero-filled
    across the allowlist.
  - **Popularity ranking:** `?sort=top&window=<hours>` and
    `/posts/trending` shortcut.
  - **Threaded replies:** optional `parent_id` on `POST /posts`,
    `GET /posts/{id}/replies`. Main feed is top-level only.

**Tests:** 158 `verify_api.py` checks + 54 pytest unit/integration tests
(cursor envelope at the HTTP boundary, concurrent-delete races, idempotency
under concurrency, FTS injection safety, reaction-kind wiring).

---

## 3. Design decisions

### 3.1 Three-layer architecture (routers → services → repositories)

```
routers/      HTTP concerns only. Headers, status codes, request bodies.
services/     Orchestration and policy. Cursor encode/decode, ownership
              checks, idempotency, parent-delete translation.
repositories/ Raw SQL via sqlalchemy.text(). No HTTP, no Pydantic.
```

A1 feedback flagged the growing monolith as a problem for "larger
assignments"; Gold features (idempotency under concurrency, reactions,
threading, FTS, ETags) are that assignment. Layering earns its keep at this
feature depth: 40 of 54 pytest tests hit services or repos directly without
`TestClient`, and the idempotency refactor required threading one
transaction through two repos — impossible cleanly without a layer. The
`require_user` dependency sits at the auth boundary so swapping identity
sources is one file.

### 3.2 Case-insensitive usernames via `COLLATE NOCASE`

Enforced once at the schema so the `UNIQUE` constraint and every
`WHERE username = :u` are case-insensitive without scattered `.lower()`
calls. Consequences:
`alice`/`Alice` → 409; `GET /users/ALICE` resolves `alice`;
`X-Username: ALICE` authenticates as `alice`; original casing is preserved
in responses. Verified end-to-end.

### 3.3 Raw SQL with `sqlalchemy.text()`

Kept from A1 and the class standard. Every query is parameterized. No ORM —
repositories return plain dicts; Pydantic handles shape at the HTTP
boundary.

### 3.4 `response_model=` as the default, with one exception

Most endpoints declare `response_model=` so FastAPI strips extras. Request
models use `ConfigDict(extra="forbid")`. The exception is `GET /posts`: the
FTS path adds a per-row `snippet` field that a fixed model would strip,
and cursor pagination wraps the list in an envelope. The service projects
each row explicitly to `_LIST_KEYS = {id, username, parent_id, message,
created_at, updated_at, reaction_counts}` — verified by
`verify_api.run_field_shape_checks` with exact key equality.

### 3.5 Hard delete on `DELETE /posts/{id}`

Spec requires 204; simplest interpretation is row removal. Soft delete
would change every downstream SELECT and complicate search — not worth it
for an assignment without audit-history requirements.

### 3.6 Centralized DB access

Every module reaches the engine through `db.engine` rather than
`from db import engine` at import time. That makes `conftest.py` a single
`monkeypatch.setattr(db, "engine", _test_engine)` instead of patching each
repo. New repos add zero test-harness surface.

---

## 4. Schema diff from A1

```sql
CREATE TABLE users (
    id         INTEGER PRIMARY KEY,
    username   TEXT NOT NULL COLLATE NOCASE,
    bio        TEXT,                              -- new (silver)
    created_at TEXT NOT NULL
        DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (username)
);

CREATE TABLE posts (
    id         INTEGER PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    parent_id  INTEGER REFERENCES posts(id) ON DELETE CASCADE,  -- new (gold)
    message    TEXT NOT NULL,
    created_at TEXT NOT NULL
        DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT                               -- new (silver, nullable)
);
```

Changes vs A1: `timestamp` → `created_at` (spec naming); `COLLATE NOCASE`
on `username`; `bio` and `updated_at` columns; auto-create-user-on-first-post
removed per spec; `parent_id` added for threading. Timestamps are UTC with
`Z` suffix; the schema-level `DEFAULT` means the repository never threads
`created_at` through INSERTs. `updated_at` is set in Python at microsecond
precision so same-second create+PATCH advances the ETag.

`post_count` is not stored — it's a correlated subquery in every
user-returning SELECT: `(SELECT COUNT(*) FROM posts WHERE user_id = u.id)`.
The invariant stays automatically correct across inserts and deletes.

**Extra tables for Gold:**

```sql
CREATE TABLE idempotency_keys (
    user_id       INTEGER NOT NULL REFERENCES users(id),
    key           TEXT    NOT NULL,
    body_hash     TEXT    NOT NULL,          -- sha256({message, parent_id})
    response_json TEXT    NOT NULL,          -- '' = claimed, not yet finalized
    created_at    TEXT    NOT NULL DEFAULT (...),
    PRIMARY KEY (user_id, key)
);

CREATE TABLE reactions (
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id    INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    kind       TEXT    NOT NULL,            -- like | laugh | heart
    created_at TEXT    NOT NULL DEFAULT (...),
    PRIMARY KEY (user_id, post_id, kind)    -- natural idempotency
);

CREATE VIRTUAL TABLE posts_fts USING fts5(
    message, content='posts', content_rowid='id'
);
-- AFTER INSERT / DELETE / UPDATE triggers keep posts_fts in sync.
```

FTS5 uses external content (`content='posts'`), so the virtual table stores
only the inverted index; the source text stays in `posts.message`. Triggers
are written once in `db.py:init_db()`.

---

## 5. verify_api.py additions

**TODO #1 — `run_delete_checks`:** Creates a throwaway post (so
`alice_post_id` stays available for later checks), asserts 204 + empty
body, 404 on re-GET, 404 on unknown id.

**TODO #2 — `run_pagination_checks`:** `limit=2` bounds length, `offset=1`
shifts the window, out-of-range limit/offset → 422.

**TODO #3 — `run_field_shape_checks`:** Set-equality on response keys
(not subset). Uses `USER_KEYS = {username, created_at, bio, post_count}`
and `POST_KEYS = {id, username, parent_id, message, created_at,
updated_at, reaction_counts}`. Tests every response path: POST response,
GET by key, list items.

**Silver, Gold, and feature-specific check suites:**

- **Silver** — PATCH bio round-trip, PATCH bio > 200 → 422,
  unknown-user → 404, `post_count == len(/users/{u}/posts)`, PATCH by
  non-author → 403, PATCH by author advances `updated_at`.
- **Gold cursor** — first page is the envelope with both keys present,
  `next_cursor` non-empty when more rows exist, every subsequent page is
  an envelope, walking to `null` returns all N posts with no duplicates,
  malformed cursor → 422, `cursor + offset=5` → 422.
- **FTS** — hits carry `snippet`, plain `/posts` does not, UPDATE/DELETE
  triggers evict/re-add rows, FTS operator input is treated as a phrase.
- **ETag** — `W/"..."` on GET, 304 on match, PATCH advances the ETag.
- **Idempotency** — same key + same body replays, different body → 422,
  per-user scoping, no Idempotency-Key → distinct rows.
- **Reactions** — 201 first / 204 repeat, cross-user counts stack,
  `GET /reactions` zero-fills kinds, `user_reactions` only when
  `X-Username` present, DELETE on missing → 404, unknown `kind` → 422,
  missing `X-Username` on PUT → 400, unknown post → 404, post delete
  cascades to reactions.
- **Bronze extras** — case-insensitive 409 + GET, `?username=` filter
  end-to-end, `Location` header on 201s, pagination bounds on
  `/users` and `/users/{u}/posts`.

---

## 6. `X-Username` and what real auth would change

`X-Username` is an identity hint, not authentication — any client can
claim any username and the server trusts it. That's fine for the
assignment and explicit in the spec; what real auth needs on top:

1. **A credential per user** — password hash at minimum, verified at login.
2. **A server-issued session token** — signed JWT or an opaque token
   indexed on the server side. The request header would carry the token,
   not the username. The server verifies the token maps to a given user
   and has not expired or been revoked.
3. **TLS** — a plaintext token on the wire is as forgeable as
   `X-Username`.

**JWT vs session cookie.** JWTs are stateless but revocation requires a
deny-list (which reintroduces state). Session cookies are a DB lookup per
request but trivially revocable (delete the row). For a BBS, session
cookies are the right default — revocation matters (logout, password
reset) and the per-request DB hit is negligible.

**What wouldn't change.** The `require_user` dependency in
`dependencies.py` is the swap point. Today it calls
`users_repo.get_id_by_username(x_username)`; under real auth it would
verify a token and look up the user by session. Router and service
layers are unchanged.

---

## 7. Silver and gold writeup

### 7.1 PATCH and DELETE ownership (silver)

`PATCH /posts/{id}` and `DELETE /posts/{id}` both require `X-Username` to
match the post's author, else 403. Applying the same rule to both
mutating verbs avoids the obvious inconsistency where DELETE would be
less restricted than PATCH. Ownership is compared by `user_id`, not
username string, so it survives any future username mutability. Under
real auth (§6) the enforcement line doesn't change — only the identity
source.

### 7.2 Cursor pagination (gold)

**Contract.** `GET /posts` always returns:

```json
{"posts": [ ... ], "next_cursor": "eyJpZCI6IDUwfQ=="}
```

Callers send the next request's `?cursor=` equal to the previous page's
`next_cursor`. `next_cursor` is `null` on the final page and on paths
where keyset pagination does not apply (offset, `?q=` search,
`?sort=top`). Envelope keys stay stable so clients parse one shape.

**Why cursor.** Offset breaks under concurrent inserts: a new post
between pages shifts `offset=50` by one, serving the boundary row
twice. Keyset pagination on `id` avoids this — inserts and deletes at
the top of the feed don't shift `id < last_seen_id`.

**Offset backward compat, with enforcement.** `?offset=` is still
accepted for callers that prefer it, but `?cursor=` + `?offset > 0` is
**422** (`"cursor and offset cannot be combined — pick one pagination
mode"`). `offset=0` alongside a cursor is the cursor path (the default
offset means "not supplied"). When `?offset=` drives pagination the
response is the same envelope with `next_cursor: null`.

**Encoding.** `urlsafe_b64(json({"id": <last_id>}))` with padding
stripped. JSON so the format is extensible (future `{"id": x,
"created_at": t}` for stable ordering under id reset). Malformed →
422 with `"Invalid cursor"`.

**First page.** No `?cursor=` needed: server fetches `limit+1`, trims,
and populates `next_cursor` if more exist. Clients can write
`while next_cursor is not None`.

### 7.3 FTS5 full-text search with bm25 and snippets (gold)

`GET /posts?q=<term>` is backed by a SQLite FTS5 virtual table
(`posts_fts`) indexing `posts.message`, synced by AFTER
INSERT/UPDATE/DELETE triggers.

**Why FTS5 over `LIKE`.** Relevance ranking via `bm25()` (rarer terms
weight higher, document length matters) and `snippet()` highlighting
(a window of match context with `<b>...</b>` delimiters and ellipses).
Both are one column in a SELECT; reimplementing over `LIKE` needs
Python-side scanning.

**Search-path response shape.** Each hit carries an extra `snippet`
field beyond the standard post keys; plain `/posts` does not. The
service projects explicitly in `_project_list_item`. See §3.4.

**Operator-injection safety.** User input is wrapped as an FTS phrase:

```python
def _fts_phrase(q: str) -> str:
    return '"' + q.replace('"', '""') + '"'
```

FTS5 supports `AND`, `OR`, `NOT`, `NEAR`, column filters. Wrapping in
double quotes forces literal-phrase matching; embedded quotes are
doubled. Tested in `tests/test_fts_injection.py`.

**Trigger sync.** The external-content FTS5 table gets its source text
from `posts` on demand, so triggers mirror every mutation — INSERT
adds, DELETE tombstones, UPDATE deletes+re-inserts. Without them a
PATCH leaves the index pointing at the pre-edit text and search
silently diverges. The verifier asserts both update directions and
the delete-eviction path.

**Cursor + feed boundary.** bm25 rank isn't monotonic in `id`, so
keyset pagination doesn't work on the search path; `?q=` + `?cursor=`
is 422. The search path also honors `top_level_only=True` — replies
don't surface in `/posts?q=` any more than they do in `/posts`.

### 7.4 Weak ETags and conditional GET (gold)

`GET /posts/{id}` emits `ETag: W/"<id>-<timestamp>"` where the
timestamp is `COALESCE(updated_at, created_at)` from the repository
SELECT. `If-None-Match` match → 304 empty body; non-match → 200 full
body. `PATCH` emits the new ETag.

Weak (`W/`) because JSON serialization isn't byte-stable across
framework versions; we claim "semantically equivalent," not "byte
identical." Timestamp-based, not payload-hash-based, because it's O(1)
and already tracked. The `updated_at` microsecond precision (§4) is
load-bearing: without it, a same-second create+PATCH doesn't advance
the ETag and clients cache stale content. No `If-Match` on PATCH yet —
that would turn PATCH into optimistic concurrency control with 412 on
stale view; the shape is already correct for that extension.

### 7.5 Idempotent POST via `Idempotency-Key` (gold)

`POST /posts` accepts an optional `Idempotency-Key` header:

- Same `(user, key)` + same body → replay the stored 201.
- Same `(user, key)` + different body → **422**.
- Same `(user, key)` while the winner is still mid-flight → **409**.
- Different user, same key → independent 201 (keys are per-user via
  `PRIMARY KEY (user_id, key)`).

**The two-phase claim.** The naive shape — `get()` to check,
`create_post()` to side-effect, `put()` to store — has a race: two
concurrent requests both pass `get()`, both insert posts, the loser
replays the winner's response while leaving a duplicate row. That's
"at most twice, report once" — not the Stripe contract.

The fix is to claim the key *before* the side effect, inside one
transaction:

```
BEGIN
  INSERT INTO idempotency_keys (..., response_json='')   -- claim; PK collision
  SELECT 1 FROM posts WHERE id = :parent_id              -- parent check
  INSERT INTO posts (...)                                -- side effect
  UPDATE idempotency_keys SET response_json = :resp      -- finalize
COMMIT
```

The composite PK is the serialization point. The loser's claim INSERT
raises `IntegrityError` before any post is created; the transaction
rolls back with no side effect, and the loser re-reads the winner's
row and replays. The empty-string `response_json` sentinel lets a
third observer tell "finalized" from "in flight" and return 409.

**Implementation shape.** `services/posts.py` opens one
`db.engine.begin()` and threads the connection through
`idem_repo.claim`, `posts_repo.get_by_id(..., conn=conn)`,
`posts_repo.create(..., conn=conn)`, `idem_repo.finalize`. The `conn=`
parameter defaults to `None` on the repo signatures, so every
non-idempotent caller keeps the one-write-per-call behavior.

**What's stored.** `body_hash = sha256({message, parent_id})` so
replaying a top-level key against a reply body is a 422. The stored
`response_json` goes through `response_model=PostResponse` on replay,
stripping internal fields — replay and live responses are identical
from the client's view.

### 7.6 Location headers and pagination consistency

`POST /users` and `POST /posts` emit `Location` headers pointing at
the created resource, per RFC 7231 §6.3.2. `GET /users` and
`GET /users/{username}/posts` accept the same `?limit=<1..200>&offset=<≥0>`
bounds as `GET /posts`, rejecting out-of-range with 422 — bronze's
limit/offset shape is now uniform across list endpoints.

### 7.7 Reactions (gold)

```
PUT    /posts/{id}/reactions/{kind}   201 created | 204 already exists
DELETE /posts/{id}/reactions/{kind}   204 | 404
GET    /posts/{id}/reactions          200 {counts, total, user_reactions?}
```

**PUT, not POST.** A reaction is fully identified by
`(user, post, kind)` — no generated id, no surprise state. PUT is
idempotent by HTTP contract and by primary key; a second identical PUT
returns 204. POST would imply "create a new reaction resource" and
force the server to invent an id.

**Fixed kind allowlist.** `like`, `laugh`, `heart`, validated at the
router via a `str` Enum so FastAPI returns 422 on anything else without
the service checking. Free-form kinds fragment counts and break the
response schema.

**Composite PK as idempotency.** `PRIMARY KEY (user_id, post_id, kind)`
pushes the uniqueness check into the schema. `reactions_repo.add()`
inserts, catches `IntegrityError`, and — importantly — disambiguates
duplicate-reaction from post-deleted-mid-request: if the row exists
after the error, it was a duplicate (→204); if not, the post
disappeared (→404 via `PostVanished`). Tested in
`test_race_conditions.py`.

**Cascade on post delete.** `posts(id) ON DELETE CASCADE` and
`users(id) ON DELETE CASCADE` on the reactions table mean deleting a
post sweeps its reactions in one transaction. The verifier reacts,
deletes the post, and confirms both are gone.

**Viewer-scoped `user_reactions`.** With `X-Username`, the response
lists the caller's own reactions (`"user_reactions": ["like", "heart"]`);
without it, the field is omitted (not set to `null`) so anonymous
callers aren't told they have zero reactions.

**Counts zero-filled.** `counts` includes every kind even when nobody
used it, so clients render a full reaction bar from one payload.

**Single source of truth for kinds.** `constants.REACTION_KINDS`. The
router enum is `Enum("ReactionKind", {k: k for k in REACTION_KINDS},
type=str)`; the repository generates the aggregate `SUM(CASE WHEN
kind='…')` expressions from it; the service uses it directly for
zero-fill. Adding a new kind is a one-line edit guarded by
`tests/test_reaction_kinds.py`.

### 7.8 Embedded `reaction_counts` on post responses (gold)

Every post response — `POST /posts`, `GET /posts`, `GET /posts/{id}`,
`PATCH /posts/{id}`, `GET /users/{u}/posts`, `?q=…`, `/posts/trending`,
`/posts/{id}/replies` — carries `reaction_counts: {like, laugh, heart}`
inline. A feed client renders per-post totals without a second request
per row.

Inline (not `?include=reactions`) because for a bulletin board feed
reaction counts are what "a post" means visually; the optional variant
would be sent on 99% of requests.

Computed by a `LEFT JOIN` against an aggregate subquery, generated
from `REACTION_KINDS`:

```sql
LEFT JOIN (
    SELECT post_id,
           SUM(CASE WHEN kind='like'  THEN 1 ELSE 0 END) AS like_count,
           SUM(CASE WHEN kind='laugh' THEN 1 ELSE 0 END) AS laugh_count,
           SUM(CASE WHEN kind='heart' THEN 1 ELSE 0 END) AS heart_count
    FROM reactions GROUP BY post_id
) rc ON rc.post_id = p.id
```

`LEFT JOIN` + `COALESCE` so posts with no reactions still return a row
with zero-filled counts. The join lives in `_POST_SELECT` so every
post-reading query — search, update-readback, replies — gets the same
shape. Counts reflect table state at query time; no cache layer.

### 7.9 Popularity ranking: `sort=top` and `/posts/trending` (gold)

`GET /posts?sort=top` ranks by reaction count; `?window=<hours>` limits
which reactions feed the ranking. `GET /posts/trending` presets
`sort=top&window=24&limit=10`.

**Two numbers, not one.** The *displayed* `reaction_counts` are always
all-time so a "this post has 42 likes" badge doesn't change when the
viewer switches windows. The *ranking score* is separately aggregated
over the window:

```sql
LEFT JOIN (
    SELECT post_id, COUNT(*) AS rank_score
    FROM reactions
    WHERE created_at >= strftime('%Y-%m-%dT%H:%M:%SZ', 'now', :window_expr)
    GROUP BY post_id
) rk ON rk.post_id = p.id
...
ORDER BY COALESCE(rk.rank_score, 0) DESC, p.id DESC
```

Tiebreaker is `id DESC` so newer posts win on rank parity.

`/posts/trending` exists as its own URL so clients link to "what's hot
right now" without constructing query strings; the server owns the
default so the interpretation doesn't drift. Thin wrapper over
`list_posts_top` — same SQL, different defaults.

`sort=top` + `cursor` → 422: rank isn't monotonic in `id`, so keyset
pagination can't preserve order. Offset works.

### 7.10 Threaded replies via `parent_id` (gold)

`POST /posts` accepts optional `parent_id`; the response echoes it.
`GET /posts/{id}/replies` lists direct children, oldest-first. The
main feed (`GET /posts`) filters `parent_id IS NULL` so replies don't
compete with top-level posts.

**`parent_id`, not a separate `comments` table.** A reply *is* a post
— same fields, validation, reactions, ETag, idempotency. A separate
table would duplicate every rule and need separate plumbing for every
per-post feature. One nullable column vs. a full second resource.

**One level deep by query.** Replies can themselves be replied to
(`parent_id` chains arbitrarily), but `/replies` returns only direct
children. Clients that want a full thread walk the tree per node.
Recursive CTEs would work but add complexity the assignment doesn't
justify.

**Cascade on delete.** `parent_id REFERENCES posts(id) ON DELETE
CASCADE` means deleting a thread root sweeps every reply in one
transaction — no router recursion, no service coupling to tree shape.
Verified: create root + 2 replies, delete root, both replies 404.

**Validation.** Unknown `parent_id` → 404 ("Parent post not found"),
not 422 — the error is about the referenced resource, not the body.
`GET /posts/{unknown}/replies` also 404, not an empty array, so
clients distinguish "no replies yet" from "post deleted."

**Parent-delete race.** Between the pre-check read and the INSERT, a
concurrent `DELETE /posts/{parent_id}` would make the FK fire as a
500. The create path wraps the INSERT in `try/except IntegrityError`
and translates to the same 404. Inside the idempotent path, the same
translation also rolls back the claim row so the key stays retryable.
Covered by `test_race_conditions.py`.
