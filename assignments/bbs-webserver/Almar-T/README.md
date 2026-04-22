# BBS Webserver — Almar-T

Gold tier submission for Assignment 2. A FastAPI layer sitting on top of
the Assignment 1 BBS database. The A1 CLI is untouched; both it and the
API now speak to the same SQLite file.

---

## 1. How to run

```bash
cd assignments/bbs-webserver/Almar-T
pip install -r requirements.txt
uvicorn main:app --port 8000
```

In a second terminal:

```bash
python verify_api.py
```

**Database location.** `db.py` resolves the DB path in this order:

1. `BBS_DB_PATH` environment variable, if set.
2. Otherwise, `../../bbs/Almar-T/bbs.db` — the A1 CLI's database file.

So out of the box, `python bbs_db.py read` in the A1 directory and
`GET /posts` here see the same posts. Set `BBS_DB_PATH` to an absolute
path if you want an isolated DB (e.g., `BBS_DB_PATH=/tmp/bbs.db uvicorn main:app`).

**Migrations.** On startup, `init_db()` walks `migrations/*.sql` and
applies any not yet recorded in the `schema_migrations` tracking table.
Every migration runs at most once per database. Safe against a fresh
DB *and* against A1's existing DB (migration `001` uses
`CREATE TABLE IF NOT EXISTS`).

---

## 2. Tier targeted

**Gold.** Features on top of bronze:

- **Silver:** `bio` + `post_count` on every user response; `PATCH /users/{username}` for bios; `PATCH /posts/{id}` with author-only enforcement via `X-Username` match; `updated_at` on the post response; `GET /posts?username=…` filter composable with `?q=` and pagination.
- **Gold (reactions):** `POST /posts/{id}/reactions`, `DELETE /posts/{id}/reactions/{username}`, plus `GET /posts/{id}/reactions` for completeness. Uses an association table.
- **Gold (boards):** `POST /boards`, `GET /boards`, `GET /boards/{name}/posts`. Posts gain a `board` field, defaulting to a seeded `general` board. Requires a real schema migration (new table + column on posts).

Two gold features, not one — the assignment permits "one of the following *or something of comparable scope*."

---

## 3. Design decisions

**Author-only PATCH on posts.** Only the original author (as identified by `X-Username`) can edit their post. An intruder sending someone else's username in the header gets 403. I considered the "anyone can edit, since `X-Username` isn't real auth anyway" position and rejected it: even a weak identity primitive should be enforced consistently, so the day we replace `X-Username` with real tokens, the authorization logic already exists in the right place. See §6 for more on this.

**Raw SQL via SQLAlchemy `text()`, not the ORM.** Kept A1's approach. The ORM would buy us typed result objects and less boilerplate, but also a vocabulary shift (sessions, flush/commit semantics, identity maps) that hides what the DB is actually doing. For a project where learning SQL is part of the point, the ORM's benefits aren't worth the opacity.

**Hard delete on `DELETE /posts/{id}`, with cascading cleanup of reactions.** The spec says hard delete, so the row is gone. I also drop any reactions referencing the post in the same transaction — no orphaned rows, no foreign-key landmines. A soft-delete flag would preserve history for moderation appeals, but it'd then require every read query to filter `WHERE deleted_at IS NULL` forever; not worth it at this scale.

**Column aliases to keep A1's CLI working.** The A1 schema calls the post-creation timestamp `timestamp`, not `created_at`, and the reaction column `emoji`, not `kind`. Renaming in the DB would break A1's CLI, which shares the file. Instead, I kept the SQL columns as-is and aliased them in the API's response-shaping layer. The API spec is satisfied; A1 keeps reading its rows under the old names; no data is duplicated.

**Migrations over a single growing `init_db()`.** Each schema change is a numbered `.sql` file tracked in a `schema_migrations` table. Nicer than the alternative (one `init_db()` function that grows unboundedly with `IF NOT EXISTS` / `ALTER TABLE` calls) because: each change is a git-reviewable diff, data backfills are natural (not awkward to retrofit), and `SELECT version FROM schema_migrations` tells you what state the DB is in. Costs ~40 lines of infrastructure in `db.py`.

**`/users/{username}/posts` as a sub-resource, not `/posts?user=…`.** The collection "Alice's posts" is genuinely a resource you might want to link to. `/posts?user=alice` is the right shape for a filter; `/users/alice/posts` is the right shape for a view of a named entity. Both exist — the filter version (silver) handles composability with `?q=` and pagination; the sub-resource version gives you a clean URL to bookmark.

---

## 4. Schema changes from A1

A1's schema is preserved byte-for-byte; A2 adds a tracking table, one column, one new table, and one more column. No renames, no drops. Concretely:

### New: `schema_migrations` (tracking table, created by `init_db()`)

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);
```

### Migration 001 — baseline (verbatim A1 schema, IF NOT EXISTS)

No-op on A1 databases; creates the schema on a fresh install.

### Migration 002 — silver

```sql
ALTER TABLE posts ADD COLUMN updated_at TEXT;
```

Nullable — existing posts get `NULL`, which the API surfaces as `"updated_at": null` (meaning "never edited"). `PATCH /posts/{id}` stamps this column.

### Migration 003 — gold (boards)

```sql
CREATE TABLE IF NOT EXISTS boards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

INSERT OR IGNORE INTO boards (name, description) VALUES ('general', 'Default board');
```

The seeded `general` board matters: migration 004 gives every existing post `board = 'general'`, so that board must exist by the time 004 runs.

### Migration 004 — gold (posts.board)

```sql
ALTER TABLE posts ADD COLUMN board TEXT NOT NULL DEFAULT 'general';
```

Existing A1 rows get `board = 'general'` via the DEFAULT; new posts default to `'general'` if the request body omits the field.

### Behavior change (not a schema change)

A1's `get_or_create_user()` auto-created missing users on first post. **A2 does not call it from the API path.** `POST /posts` with `X-Username: alice` returns 404 if no user named Alice exists; users must be created via `POST /users` first. A1's CLI still has its old auto-create behavior; the change is purely in the API layer.

---

## 5. What I added to `verify_api.py`

### Modifications to shipped checks

Two shipped assertions hard-coded the bronze response shapes:

- `POST /users` response was asserted equal to `{username, created_at}` (line 131-135).
- `POST /posts` response was asserted equal to `{id, username, message, created_at}` (line 180-185).

Silver and gold add fields to both responses (`bio`, `post_count`, `updated_at`, `board`). The shipped checks would fail against a spec-conformant silver/gold API. I updated both to expect the gold shape and prefixed the check names with `(gold shape)` so the upgrade is visible in the test output. Full explanation lives in a comment block at the top of `verify_api.py`.

### STUDENT TODO #1 — `run_delete_checks`

- `DELETE /posts/{id}` on an existing post returns 204 with an empty body.
- `GET /posts/{id}` after the delete returns 404.
- `DELETE /posts/99999999` (nonexistent) returns 404.

Creates its own victim post instead of reusing `state["alice_post_id"]`, so later checks that assume Alice's post still exists don't break.

### STUDENT TODO #2 — `run_pagination_checks`

- `GET /posts?limit=3` returns at most 3 items.
- `GET /posts?offset=2` returns exactly the slice `base[2:]` — i.e. the first two items are actually skipped in order, not just random dropouts.
- `GET /posts?limit=0` returns 422.
- `GET /posts?limit=500` returns 422.
- `GET /posts?offset=-1` returns 422.

Seeds 5 setup posts first so the limit=3 assertion is non-trivial against a small DB.

### STUDENT TODO #3 — `run_field_shape_checks`

Asserts `set(body.keys()) == EXPECTED_SHAPE` on every endpoint that returns a user or a post:

- `POST /users`, `GET /users/{u}`, items in `GET /users`
- `POST /posts`, `GET /posts/{id}`, items in `GET /posts`

Uses set equality, not subset — a stray `email` or `user_id` would fail.

### Silver extensions

- `PATCH /users/{u}` — 200 on success, 200 bio matches, 422 on over-length bio, 404 on unknown user.
- `PATCH /posts/{id}` — 200 as author, 200 sets `updated_at`, 200 message was updated, 200 response has post shape, 403 as non-author, 400 without `X-Username`, 422 on empty message, 404 on unknown post.
- `post_count` — starts at 0 for new users, tracks posts made.
- `bio` — defaults to empty string.
- `?username=` filter — returns only that user's posts, composes with `?q=` and `?limit=`.

### Gold extensions

- Reactions: 201 on create, shape assertion, duplicate → 409, unknown user → 404, unknown post → 404, 204 on delete, double-delete → 404.
- Boards: `general` seeded, board shape assertion, 201 on create, duplicate → 409, invalid name → 422, creating a post in the board reflects it, unknown board on post → 404, `/boards/{name}/posts` returns only that board's posts, unknown board → 404.

### Edge cases beyond the spec

- `DELETE /posts/{id}` has an *empty response body* (not just status 204) — the spec says 204, and 204 implies no body, but the verifier now asserts it explicitly.
- `PATCH /posts/{id}` without `X-Username` returns 400, mirroring `POST /posts` semantics. The spec doesn't explicitly require this, but it's the consistent behavior.
- Double-delete a reaction → 404. Protects against idempotence confusion.

---

## 6. `X-Username` and auth

`X-Username` is not authentication. Anyone can send any name in that header and the server will accept it. In practice this means my "author-only PATCH" enforcement is theater: an intruder who knows Alice's username can edit Alice's posts by sending `X-Username: alice`. The verifier even relies on this — it impersonates users freely to test authorization paths.

For real authentication we'd need, at minimum:

1. **A way to prove identity.** A password (checked against a hash), an OAuth token, or a signed session cookie. The request must carry something the server can verify that an attacker can't forge.
2. **Somewhere to keep the secret state.** A `users.password_hash` column or a sessions table, plus the cryptographic machinery to hash/verify (`bcrypt`, `argon2`) and to issue/validate tokens (JWT signing keys, or a server-side session store).
3. **A wall between identity and identification.** `X-Username` is *identification* (who you claim to be); an auth token is *authentication* (proof you are who you claim). The API surface barely changes — `POST /posts` still wants to know who's posting — but the server stops trusting whatever the client writes in a header.

The design choice to do author-only enforcement now (rather than "anyone can edit, since auth is fake anyway") is deliberate. When real auth lands, the ownership *policy* is already in place; only the *identity source* changes — swap `x_username: str = Header(...)` for `user = Depends(current_user)` and the rest of the handler is unchanged.

---

## 7. Silver & gold: what I added and why

**Silver — `bio`, `post_count`, PATCH endpoints, `?username=` filter.** The spec prescribes these directly; the interesting design choice was PATCH ownership (§3, §6 — author-only). `post_count` is computed via `SELECT COUNT(*) FROM posts WHERE user_id = ?` on every user read, not denormalized into a column. At A2's scale this is fine; at scale you'd either materialize a view, cache in Redis, or maintain a counter column with triggers.

**Gold — reactions.** Wanted to expose something the A1 data model already knew about. A1's CLI had an emoji-reactions feature with its own table; the API just surfaces it (with one renaming: column `emoji` → API field `kind`, because the A2 spec uses `kind`). Reactions are uniqued on `(post_id, user_id, emoji)`, so a double-POST with the same kind returns 409 rather than silently inserting a duplicate.

**Gold — boards.** Picked this as the second gold feature because it's the one that requires the most real engineering: a new resource with its own CRUD, a referential relationship from posts, a real schema migration including a data default, and a seeded row so existing posts don't become orphans. Every post now lives in a board; the default `general` board exists from migration 003 onward so the `NOT NULL DEFAULT 'general'` in migration 004 is satisfiable against legacy rows.

The two features are genuinely independent — reactions could go without boards and vice-versa — which is why I did both. "One gold feature or something of comparable scope" reads to me as "pick something substantial"; two coherent gold features were easier than one contrived one.
