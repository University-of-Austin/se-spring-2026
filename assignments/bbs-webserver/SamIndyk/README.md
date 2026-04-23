# BBS Webserver (Assignment 2)

FastAPI layer on top of the A1 SQLite BBS.

## Tier targeted

**Gold.** All bronze endpoints work per the spec, all three student TODOs in
`verify_api.py` are implemented, every silver feature is implemented, and the
gold feature is **reactions** (an association table plus nested resource routes
on `/posts/{id}/reactions`).

## How to run

Requirements: Python 3.10+.

```bash
pip install -r requirements.txt
uvicorn main:app --port 8000
```

The server auto-creates `bbs.db` in the working directory on startup. There
is no migration step — A1 and A2 use different enough schemas that the
intended workflow is a fresh A2 database. If you want a truly clean slate,
stop the server, delete `bbs.db`, and restart.

To run the verifier in a second terminal:

```bash
python verify_api.py
```

It prints one `PASS` / `FAIL` line per check and exits non-zero on failure.
Usernames are suffixed with a random run id, so it is safe to re-run against
the same database.

## Design decisions

- **Raw SQL over the ORM.** Kept A1's SQLAlchemy Core style (`engine` +
  `text(...)` with bound parameters). The data model is small enough that the
  ORM would be pure ceremony, and raw SQL keeps the translation from HTTP
  request to database query easy to follow. All parameters are bound, so
  injection is not a concern.
- **Hard delete for posts.** `DELETE /posts/{id}` physically removes the row
  (plus any reactions on it, via `ON DELETE CASCADE`). The alternative is a
  soft-delete flag, which would mean filtering `WHERE deleted_at IS NULL` in
  every list/get query and a policy for whether deleted posts still count
  toward `post_count`. For a BBS with no moderation requirements and no
  "undo delete" feature, that complexity is not justified yet.
- **`extra="forbid"` on all Pydantic models.** Unknown body fields return
  422 rather than being silently ignored. This catches client typos early
  (e.g. `{"msg": "..."}` instead of `{"message": "..."}`) and makes the
  contract explicit.
- **Author-only PATCH on posts.** `PATCH /posts/{id}` requires
  `X-Username` to match the original author, and returns 403 otherwise.
  `X-Username` is not real authentication, so this is only a guard rail, but
  the alternative ("anyone can edit anyone's post") feels wrong even as a
  placeholder — it would need to be undone when we switch to real auth
  anyway. Better to set the right-shaped policy now.
- **Aggregated reactions dict on every post response.** `post.reactions` is
  a `{kind: count}` map computed from the reactions table. This means a
  client that renders posts does not need a second round-trip to display
  reaction counts, at the cost of one extra small query per post in the list
  endpoints. A flat list of reaction rows is still available via
  `GET /posts/{id}/reactions` when you need per-user detail.
- **`201` for create, `204` for delete, `422` for body/query validation,
  `409` for uniqueness conflicts, `400` reserved for the missing
  `X-Username` header.** The status-code table in the spec is followed
  exactly. Notably: out-of-range `limit` / `offset` is 422 (Pydantic
  `Query(ge=..., le=...)`), not 400; that's what the framework produces and
  it's consistent with the "validation error" meaning of 422.

## Schema changes from A1

A1 schema (relevant parts):

```sql
CREATE TABLE posts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    message    TEXT    NOT NULL,
    timestamp  TEXT    NOT NULL,
    parent_id  INTEGER REFERENCES posts(id)
);
```

A2 schema:

```sql
CREATE TABLE posts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message    TEXT    NOT NULL,
    created_at TEXT    NOT NULL,     -- renamed from `timestamp`
    updated_at TEXT                  -- new, null until first PATCH
);

CREATE TABLE reactions (             -- new (gold)
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id    INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind       TEXT    NOT NULL,
    created_at TEXT    NOT NULL,
    UNIQUE (post_id, user_id, kind)
);
```

`users` is unchanged (it already had `bio TEXT NOT NULL DEFAULT ''` from A1's
gold profile feature, which silver now exposes).

Changes and why:

1. **`posts.timestamp` → `posts.created_at`.** Matches the API field name
   so row-to-dict mapping is a straight column lookup rather than an alias
   dance. Trivial rename, pure win.
2. **`posts.updated_at` added (nullable).** Required by silver's
   `PATCH /posts/{id}`. Nullable so "never edited" is a distinct state from
   "edited".
3. **`posts.parent_id` removed.** A1 had threaded replies; A2's REST spec
   does not model them. Carrying the column unused would lie about the
   data model.
4. **`reactions` table added** for the gold feature. Primary key on
   `(post_id, user_id, kind)` means the same user can react multiple kinds
   to the same post (e.g. `+1` and `heart`) but cannot duplicate a single
   kind (409 on re-post).
5. **Auto-create-user logic removed from the post-insert path.** A1's
   `get_or_create_user` helper would silently create a new user on first
   post; A2 returns 404 if `X-Username` names a user that does not exist.
   This is the behavior change called out in the spec — the `users`
   collection is now the authoritative source and must be populated via
   `POST /users` first.

## What I added to `verify_api.py`

### Bronze (the three required TODO functions)

- `run_delete_checks` — 204 on delete of an existing post, 404 on GET after
  delete, 404 on delete of a non-existent id. **Extra assertion:** a second
  DELETE of the just-deleted id must also 404 (guards against the trivially
  broken implementation that returns 204 for any id).
- `run_pagination_checks` — creates five posts, then checks `?limit=3` caps
  at 3, `?offset=2` equals `list[2:]` of the unsliced list (this is
  stronger than the spec's "skips the first K items" — asserting exact
  slice equality catches off-by-one or re-ordering bugs), and 422 on
  `limit=0`, `limit=500`, `offset=-1`.
- `run_field_shape_checks` — exact set equality on `set(body.keys())` for
  user and post shapes on every endpoint that returns one. Checks
  `POST /users`, `GET /users/{u}`, items in `GET /users`, `POST /posts`,
  `GET /posts/{id}`, and items in `GET /posts` (scoped by `?username=` to
  a fresh user so the assertion is not polluted by earlier runs).

### Updated bronze shape constants

Because this submission goes to gold, user responses include
`{bio, post_count}` and post responses include `{updated_at, reactions}` on
every read. The two shipped field-equality assertions in `run_user_checks`
and `run_post_checks` were updated to the gold shape (`USER_KEYS` and
`POST_KEYS` constants at the top of the file). Without that change the
bronze checks would correctly flag the silver/gold additions — the
"extend verify_api.py with assertions for the silver features you added"
instruction implies exactly this update.

### Silver

- `run_patch_user_checks` — 200 with refreshed bio, 404 on missing user,
  422 on oversize bio, and 200-with-unchanged-bio when the body is `{}`
  (partial-update semantics: omitted fields are preserved).
- `run_patch_post_checks` — 200 as author (also asserts `updated_at` is
  now non-null), **403 as non-author** (this is the ownership policy),
  a follow-up GET that confirms the non-author PATCH did not mutate the
  row, 400 on missing `X-Username`, 404 on missing post, 422 on empty /
  oversize messages.
- `run_filter_by_username_checks` — asserts the author filter on its own,
  composed with `?q=`, composed with `?limit=`, and 422 when the
  `username` query param fails the regex.

### Gold

- `run_reaction_checks` — POST with full shape check, 409 on duplicate
  `(user, kind)` pair, success on a second kind from the same user,
  aggregate `post.reactions` dict reflects the right counts, GET on the
  reactions list returns the right number of rows with the right shape,
  404s for missing post / missing user, 422s for empty kind / invalid
  username, DELETE removes all reactions from that user on that post,
  a second DELETE 404s (nothing left), and DELETE 404s for missing
  post / missing user.

## X-Username and auth

`X-Username: alice` is identity metadata, not authentication. Anyone
sending the request chooses what goes in that header, and the server
believes them. That's fine for an assignment and fine for an internal
demo, but it would fall apart the moment the API faced the open internet:
Bob could post as Alice by changing one header, Eve could delete any
post, and the author-only PATCH policy would be meaningless.

Turning this into real auth would mean splitting "who claims to be
posting" from "who the server has proof of being":

1. A separate `POST /auth/login` (or OAuth / SSO flow) that takes a
   credential and mints a short-lived token — a JWT, an opaque session
   id, whatever.
2. Every mutating endpoint requires `Authorization: Bearer <token>`.
   The server validates the token (signature for JWT, lookup for opaque
   ids), resolves it to a username, and uses **that** username as the
   effective identity. `X-Username` goes away entirely.
3. Passwords (or external identity) need a place to live:
   `users.password_hash` on the table, or a delegation to an IdP.
4. HTTPS becomes non-optional — tokens in plaintext over HTTP are
   roughly as bad as no auth.
5. The author-only PATCH check stops being a guard rail and becomes the
   actual authorization layer: `effective_user_from_token == post.author`.

Everything built in this assignment that references `X-Username` (the
create-post flow, PATCH ownership, reactions) is structured so that when
the header is replaced by a token-derived identity, only the "where does
the username come from" helper changes — the authorization logic that sits
on top is already in place.

## Silver/gold features and why

### Silver

- **`bio` and `post_count` on every user response.** `bio` is a real column;
  `post_count` is computed on the fly with `SELECT COUNT(*) FROM posts
  WHERE user_id = :uid`. Computing it instead of caching it is the right
  default: caching would mean keeping a counter in sync across post create /
  delete, and the list endpoint fires N+1 of these queries but the scale
  here does not warrant denormalizing.
- **`PATCH /users/{username}`** for bio edits. 200 / 404 / 422 per the spec.
  `bio` is optional in the body, so `{}` is a valid "no-op" PATCH. This
  matches standard PATCH semantics and is why the verifier includes that
  case.
- **`PATCH /posts/{id}`** for message edits, with an `updated_at` on the
  post set at edit time. Ownership is author-only (403 on mismatch). See
  the design-decisions section above for why.
- **`GET /posts?username=alice`** for author filtering, composable with
  `?q=`, `?limit=`, `?offset=`. The same regex that guards `POST /users`
  usernames applies here so we cannot end up executing a `LIKE` against a
  user-provided pattern containing `%`.

### Gold — reactions

Resource shape:

- `POST   /posts/{id}/reactions`            body `{username, kind}` → 201
- `GET    /posts/{id}/reactions`            list all reactions on a post
- `DELETE /posts/{id}/reactions/{username}` remove **all** of that user's
   reactions on that post

A reaction is `(post_id, user_id, kind, created_at)` with a uniqueness
constraint on `(post_id, user_id, kind)`. That choice means one user can
react with multiple kinds on the same post (`+1` and `heart` both
allowed), but cannot duplicate a single `(user, kind)` pair (returns 409).

`GET /posts/{id}` and items in `GET /posts` carry a `reactions` field that
is the aggregated `{kind: count}` map, so a feed renderer can show
reaction counts without a second round-trip.

I picked reactions over cursor-based pagination because the spec's cursor
option would have required either breaking the bronze `?offset=` tests
(spec says "replace") or building two pagination schemes side by side;
reactions is a strictly additive feature, which keeps the bronze surface
untouched.
