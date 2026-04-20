# BBS Webserver

FastAPI wrapper around the A1 BBS database. **Tier: Silver.**

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
FastAPI startup). If you want a fresh database, stop the server, delete
`bbs.db`, and restart. There is no standalone A1-to-A2 migration script,
since the schema is a strict subset rewrite rather than an additive change;
if you want to import old data, use your A1 export flow and then
`POST /users` + `POST /posts` against this server.

## Tier targeted

**Silver.** All 8 bronze endpoints, plus:

- `bio` (optional, max 200 chars) and `post_count` on every user response
- `PATCH /users/{username}` to update a user's bio
- `PATCH /posts/{id}` to edit a post's message; adds `updated_at`
- `GET /posts?username=alice` to filter by author (composes with `?q=`, `?limit=`, `?offset=`)

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
    bio TEXT
);
```

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

The `X-Username` header is identity metadata, not authentication. Anyone
can send any username — the server trusts it. In practice, that means
everyone who can reach the server can post as anyone, edit anyone's
post (if the ownership policy is enforced purely from this header), and
so on. It's the weakest possible form of identity.

Real authentication would need a step that the client can't fake: the
server has to be able to tell "this request is really from alice" from
"this request claims to be from alice." The standard answer is a shared
secret the client proves knowledge of without revealing it — a password
exchanged at login, then a signed token (JWT, session cookie) on every
subsequent request. The signature on the token is what the server
can't forge, so the username it contains is trustworthy. We'd also
probably move the principal onto the token rather than a separate
header, and the PATCH ownership check in main.py would compare
`token.username == post.author` instead of `header.username == post.author`.

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
