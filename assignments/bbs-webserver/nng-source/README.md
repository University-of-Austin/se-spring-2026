# BBS Webserver

FastAPI wrapper around the A1 BBS database. **Tier: Gold.**

Bronze and Silver are both covered per the PDF. The Gold tier is met
with **two** features on top of Silver:

1. **Password auth** — users register with a password, log in to receive
   a bearer token, and all write endpoints require that token.
2. **Boards/topics** — posts belong to a named board (`#general` by
   default), with `/boards` and `/boards/{name}/posts` endpoints.

A terminal UI at `/` and cross-page navigation round out the
experience but aren't the gold feature — the auth and boards work are.

## How to run

```bash
pip install -r requirements.txt
uvicorn main:app --port 8000
```

Open another shell in the same directory and run the verifier:

```bash
python verify_api.py
```

Tables are created automatically on first request (`db.init_db()` runs on
FastAPI startup). If you have an older `bbs.db` from before password
auth was added, `init_db()` best-effort-adds the `password_hash` column
on startup; pre-existing users will have `password_hash = NULL` and
cannot log in until you re-create them via `POST /users`. Easiest path
for a clean demo: stop the server, delete `bbs.db`, restart.

Open **`http://localhost:8000/`** in a browser for the terminal UI, or
**`/docs`** for Swagger. Every page has a top-right nav strip linking
to the others.

## Tier targeted

**Gold.** All 8 bronze endpoints + all silver additions + two gold
features (password auth and boards). Summary of each layer:

**Bronze** (per A2 spec): `POST/GET /users`, `GET /users/{u}`,
`GET /users/{u}/posts`, `POST /posts` (with `X-Username`), `GET /posts`
(with `?q=`, `?limit=`, `?offset=`), `GET /posts/{id}`,
`DELETE /posts/{id}`.

**Silver** additions:
- `bio` (optional, max 200 chars) and `post_count` on every user response
- `PATCH /users/{username}` to update a user's bio
- `PATCH /posts/{id}` to edit a post's message; adds `updated_at`
- `GET /posts?username=alice` filter composable with `?q=` and pagination

**Gold** additions:
- **Passwords**: scrypt-hashed, opaque bearer tokens, `/login`, `/logout`
  (see X-Username / auth section)
- **Boards**: posts have a `board` field defaulting to `"general"`;
  `GET /boards`, `GET /boards/{name}`, `GET /boards/{name}/posts`;
  `GET /posts?board=tech` filter composable with other filters

## Design decisions

- **Raw SQL, not ORM.** Kept the A1 pattern — `sqlalchemy.text()` with bound
  parameters everywhere. The assignment is small enough that the raw SQL
  stays readable and the concrete queries make it obvious when a handler is
  doing extra work (e.g. the N+1 on `GET /users` that computes `post_count`
  per row). If this grew, I'd swap to the ORM or add a CTE.
- **Hard delete, not soft delete.** `DELETE /posts/{id}` removes the row
  entirely. Soft delete (a `deleted_at` column) would be nicer if we
  wanted restore/undo or moderation audit trails, but the spec asks for
  "hard delete" and the verifier asserts a subsequent GET returns 404, so
  hard delete is the straightforward implementation.
- **`updated_at` is nullable and always present.** I include `updated_at`
  on every post response (`null` until the post is edited) rather than
  conditionally adding the key. This keeps the post response shape constant
  across Bronze-style GETs and Silver-style PATCH results, which makes the
  strict field-shape check in `verify_api.py` simpler and easier to reason
  about for a frontend consumer.
- **PATCH ownership policy:** enforced via `X-Username` header match.
  Only the original author can edit their post; a mismatched header
  returns 403, a missing header returns 400. This mirrors the pattern
  used on `POST /posts` and is the more conservative of the two options
  the spec offers — it at least makes it intentional when an actor edits
  someone else's post (they have to send a different header), even though
  it's not real authentication. Documented again in the X-Username
  section below.
- **URL shape: `/users/{username}/posts` vs `/posts?username=`.** I kept
  both. `/users/{username}/posts` returns 404 when the user doesn't exist
  (the verifier requires this), which makes it the right shape for "show
  me this person's wall." `/posts?username=` silently returns an empty
  array for an unknown user, which is the right shape for filter
  composition with `?q=` and pagination where a missing user isn't really
  an error.

## Schema changes from A1

A1 auto-created users the first time someone posted. A2 does not:
`POST /posts` with an unknown `X-Username` returns 404.

```sql
-- A1 users
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    bio TEXT DEFAULT '',
    joined TEXT NOT NULL
);

-- A2 users
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL,
    bio TEXT,
    password_hash TEXT  -- scrypt(salt$hash) in hex; see auth section
);

-- New in the auth extension
CREATE TABLE sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- New in the boards extension (A2 PDF lists boards as a Gold feature)
CREATE TABLE boards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL
);
-- posts.board_id FK added (NOT NULL, defaults to the seeded "general" board).
```

A "general" board is seeded by `init_db()` on startup so posts without
an explicit board always have a home.

Renamed `joined` → `created_at` to match the API response field. `bio`
defaults to `NULL` now instead of `''` so "unset bio" is distinguishable
in JSON responses (`null` vs `""`).

```sql
-- A1 posts (had boards + threads from A1 silver)
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    board_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    reply_to INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (board_id) REFERENCES boards(id),
    FOREIGN KEY (reply_to) REFERENCES posts(id)
);

-- A2 posts
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

Dropped `board_id`, `reply_to`, and the `boards` table entirely — this
assignment's spec doesn't expose them, and keeping dead columns would
have been a foot-gun for the verifier. Renamed `timestamp` →
`created_at` to match the API, and added `updated_at` for the Silver
PATCH behavior. Auto-create-user code path was removed from the post
insertion logic.

## Verifier status

**101 passed, 0 failed.** Breakdown: the shipped bronze checks
(adjusted for silver/gold shapes), silver bio/post_count/PATCH/ownership
checks, TODO #1/#2/#3, 15 auth-specific assertions, 18 board-specific
assertions.

## What I added to verify_api.py

**TODO #1 (`run_delete_checks`)** — the three spec behaviors (204 on
delete of existing, 404 on subsequent GET, 404 on delete of nonexistent),
plus one extra: **deleting an already-deleted post returns 404** (same
behavior as deleting a never-existing post, which I wanted to pin down).

**TODO #2 (`run_pagination_checks`)** — the five spec behaviors (limit
caps, offset skips, 422 on limit=0/500/offset=-1), plus one extra:
**consecutive pages of size 1 don't return the same row**. The 200/OK
+ non-overlap check catches the common off-by-one where `OFFSET` is
ignored.

**TODO #3 (`run_field_shape_checks`)** — strict set equality on response
keys for every user/post shape the spec lists. I updated the shipped
bronze-shape assertions on `POST /users` and `POST /posts` to match the
Silver response shape (users gain `{bio, post_count}`; posts gain
`{updated_at}`), since my server is at Silver tier.

**Gold board extensions (`run_board_checks`):** posting with no board
lands in `general`; posting with an explicit board round-trips;
invalid board names (spaces, 31 chars) return 422; `GET /boards`
returns the expected shape `{name, created_at, post_count}` and
includes the seeded `general`; `GET /boards/{name}` returns 200 for
real boards and 404 for unknown; `GET /boards/{name}/posts` filters
correctly and returns the gold post shape with `board` in every item;
`GET /boards/{unknown}/posts` returns 404; `?board=` on `/posts`
composes with `?username=`.

**Gold auth extensions (`run_auth_checks`):** `POST /users` without a
password or with a <8 char password returns 422; `POST /login` with the
wrong password or an unknown user returns 401; write endpoints without
a token return 401, with an invalid token return 401, with a token
that doesn't match `X-Username` return 403; `PATCH /users/{u}` as
someone else returns 403; `DELETE /posts/{id}` as non-author returns
403; `POST /logout` revokes the token (subsequent writes 401).

**Silver extensions:**

- `run_silver_user_checks` — new user bio is `null`, post_count starts
  at 0 and increments after posts, PATCH bio round-trips, bio over 200
  chars returns 422, PATCH on unknown user returns 404.
- `run_silver_post_checks` — new post `updated_at` is `null`, author
  PATCH sets `updated_at` and the new message is persisted, non-author
  PATCH returns 403 (ownership policy), missing X-Username on PATCH
  returns 400, PATCH on unknown post returns 404, PATCH with empty
  message returns 422 (shares the POST validator), `?username=` filter
  returns only that author's posts, `?username=` composes with `?q=`
  and returns only rows matching both predicates.

## X-Username and auth

`X-Username` on its own is identity metadata, not authentication. Anyone
can send any username — the server would have no way to tell "this
request is really from alice" from "this request claims to be from
alice." The standard fix is a shared secret the client proves knowledge
of without revealing it — a password exchanged at login, then a signed
or opaque token on every subsequent request — plus a hash of the
password at rest so the database isn't a liability if it leaks.

This implementation does that:

- `POST /users` now requires `password` (min 8 chars). The password is
  hashed with `hashlib.scrypt` (stdlib, memory-hard KDF) using a fresh
  16-byte random salt per user and stored as `salt$hash` in hex in the
  `users.password_hash` column. Plaintext is never persisted.
- `POST /login` verifies the password with `secrets.compare_digest`
  (constant-time comparison) and returns a `{token, username}` pair.
  The token is a 32-byte `secrets.token_urlsafe(...)` value — opaque to
  the client, looked up server-side in a `sessions` table. I used a DB
  session table instead of a JWT because it's simpler to reason about,
  revokable (see `POST /logout`), and doesn't require juggling a signing
  secret for a 10-15 hour homework.
- All write endpoints (`POST /posts`, `PATCH /posts/{id}`,
  `DELETE /posts/{id}`, `PATCH /users/{username}`) now require
  `Authorization: Bearer <token>`. Missing or invalid token returns 401.
  A token that doesn't match the `X-Username` header or the resource
  owner returns 403.
- `DELETE /posts/{id}` is now author-only (previously anyone could delete).
- `POST /logout` deletes the session row, so the token is immediately
  dead; further requests with it return 401.

This is still not production-grade auth — there's no rate limiting on
login, no password rotation/reset flow, no session expiry, and the
token travels unencrypted over HTTP (fine for localhost but would need
HTTPS in the wild). But it closes the "anyone can post as anyone"
hole: without the right password you can't get a token, and without
a token you can't write.

The A2 spec calls `X-Username` "identity metadata, even before we have
real auth." I treated that as an invitation to do auth — `X-Username`
is still on the wire for continuity with the spec, but now both it and
the bearer token have to agree for a write to go through.

## Extras beyond Silver

### Browser terminal frontend

A retro green-on-dark command-line UI at `/` that talks to the same API.
Commands: `register`, `login`, `logout`, `post`, `read`, `search`,
`mine`, `user`, `users`, `get`, `edit`, `delete`, `bio`, `whoami`,
`clear`. Session token is stored in `localStorage`, so reloads keep
you logged in. Up/down arrow cycles history. Spheal mascot ported over
from A1 as the ASCII boot banner, with a cyan→blue→magenta gradient
matching the terminal theme.

### Cross-page navigation

Every HTML-returning endpoint (`/`, `/docs`, `/redoc`) gets a fixed
top-right nav strip with links to all four pages including
`/openapi.json`. FastAPI's built-in `/docs` and `/redoc` routes are
disabled and re-implemented so the nav strip can be injected into
their HTML.

### Password auth (Gold)

See the X-Username section above for the full write-up. TL;DR: scrypt
password hashing, opaque bearer tokens, sessions table, `/login` and
`/logout` endpoints, all write operations now require a valid token
whose user matches both the `X-Username` header and the resource owner.

### Boards / topics (Gold)

Posts are scoped to named boards. The boards resource matches the PDF's
Gold suggestion: a `boards` table, `board_id` FK on posts, and two new
endpoints.

- `POST /posts` accepts an optional `board` field (string, 1-30 chars,
  pattern `^[a-z0-9_-]+$`). Missing / null / empty → `"general"`. The
  board is auto-created on first post, so there's no explicit
  "create board" endpoint; boards exist precisely when something has
  been posted to them.
- `GET /boards` returns `[{"name", "created_at", "post_count"}, ...]`,
  including `general` even if empty because `init_db()` seeds it.
- `GET /boards/{name}` returns one board (404 if unknown).
- `GET /boards/{name}/posts` lists posts on that board (404 if board
  doesn't exist). Composable with `?q=`, `?username=`, `?limit=`,
  `?offset=` — exactly the same filter semantics as `GET /posts`.
- `GET /posts?board=tech` filter on the main posts list, composable
  with all other filters.

Board names are normalized to lowercase in the database, so the
terminal's `#Tech`, `#TECH`, and `#tech` all refer to the same board.

The post response shape now includes `board`:

```json
{
  "id": 17,
  "username": "alice",
  "board": "general",
  "message": "hello",
  "created_at": "2026-04-21T14:01:32",
  "updated_at": null
}
```

The field-shape check in the verifier was bumped to match.

## Silver: what I added and why

Bio and post_count give the API the minimum profile surface a frontend
would actually render on a user page — join date, vanity number, and
a freeform blurb. PATCH for bios and messages are the obvious CRUD gaps
between A1 and anything you'd want to ship. `?username=` filter
composes cleanly with the existing `?q=` and pagination, so you can
already do "show me alice's posts containing 'python'" without adding
a new endpoint.

I deliberately did not add board/topic support back (A1 had it under
Silver) because A2's spec calls boards a Gold feature, and mixing the
two would muddy the response shape.
