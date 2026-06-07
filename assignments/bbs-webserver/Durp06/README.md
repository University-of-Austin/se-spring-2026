# BBS Webserver (Assignment 2)

## 1. How to run
- Install: `pip install -r requirements.txt`
- Run server: `uvicorn main:app --port 8000`
- Run verifier: `python verify_api.py` (in another shell)
- Run internal tests: `pytest`

## 2. Tier targeted
Gold (cumulative -- bronze + silver + gold all implemented).

## 3. Design decisions
- Raw SQL via SQLAlchemy `text()` retained from A1 for continuity. All queries now live in `queries.py` -- this fixes the A1 review feedback that queries had drifted between `bbs_db.py` and `tui.py`. Route handlers in `main.py` never write SQL.
- Hard delete chosen for `DELETE /posts/{id}` (row removed from DB, not a soft-delete flag). The spec requires `204` on success and `404` on subsequent GET of the same id, which is simpler to implement and reason about with hard delete.
- `PATCH /posts/{id}` ownership policy uses three distinct status codes: `400` (header missing -- request is malformed), `404` (post doesn't exist), `403` (post exists but header names a different author -- request is well-formed but forbidden). This keeps the meanings distinct per the HTTP spec.
- Cursor encoding is `base64.urlsafe_b64encode(json.dumps({"id": <last_id>}))`. Base64 is URL-safe and opaque to clients (discourages them from parsing or incrementing it); JSON inside lets us extend the cursor shape later without breaking old clients.
- Cursor handles concurrent inserts better than offset: if a row is inserted between page 1 and page 2 of an offset-based query, offset re-counts from the top and either skips a row (insert before current offset) or duplicates one (insert after). A cursor pinned to `last_seen_id` continues from that anchor regardless of what gets inserted before it.

## 4. Schema changes from A1
- A1 auto-created a user on first post (`_get_or_create_user` in `bbs_db.py`). A2 **removes** this -- `POST /posts` with an unknown `X-Username` returns 404.
- A2 keeps `users.bio TEXT NOT NULL DEFAULT ''` from A1.
- A2 renames `users.joined` to `users.created_at` (to match the response field name).
- A2 adds `posts.updated_at TEXT NOT NULL` for silver PATCH support.
- A2 drops all other A1 tables: `boards`, `messages`, `reactions`, `votes`, `achievements`, `high_scores`. They are not in Assignment 2's scope.

DDL diff (A2 `users`):

```sql
CREATE TABLE users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT    UNIQUE NOT NULL,
    bio        TEXT    NOT NULL DEFAULT '',
    created_at TEXT    NOT NULL
);
```

DDL (A2 `posts`):

```sql
CREATE TABLE posts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    message    TEXT    NOT NULL,
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## 5. What I added to verify_api.py
- Bronze TODO #1: `run_delete_checks` -- 204 on delete, 404 on subsequent GET, 404 on delete of non-existent id.
- Bronze TODO #2: `run_pagination_checks` -- `?limit=N` caps result count; `?offset=K` skips rows; `?limit=0`, `?limit=500`, `?offset=-1` all return 422.
- Bronze TODO #3: `run_field_shape_checks` -- set-equality on response keys (no extras, no missing) at every endpoint that returns a user or post.
- Silver: `run_silver_user_checks` (bio + post_count + PATCH bio), `run_silver_patch_post_checks` (PATCH ownership matrix with 200/400/403/404/422), `run_silver_filter_checks` (`?username=` filter on GET /posts), and updated field-shape check now asserts `{username, created_at, bio, post_count}` for users and `{id, username, message, created_at, updated_at}` for posts.
- Gold: `run_gold_cursor_checks` -- pages through all posts via `?cursor=`, asserts envelope shape, no duplicate ids across pages, no gaps, final `next_cursor == null`, malformed cursor -> 422, and the bare-array path still works when `cursor` is absent.

## 6. X-Username and "authentication"
`X-Username` is a client-asserted identity header. The client tells us who it claims to be; we trust the string. There is no cryptography, no login, no session, no proof. Anyone who can send an HTTP request can impersonate any user by changing the header value. This is deliberately chosen for this assignment to teach header-based identity plumbing, but it is not authentication.

Real authentication would require, at minimum: (1) a trusted credential issuer (a login endpoint that verifies a password or OAuth token and mints a session token or signed JWT), (2) server-side verification of that token on every protected request, (3) TLS on every hop so the token isn't sniffed, (4) CSRF protection if browsers are clients (SameSite cookies or double-submit tokens), (5) replay/expiry handling (short-lived tokens + refresh, or nonces), and (6) some form of session revocation (server-side store for session tokens, or a short JWT TTL).

## 7. Silver and gold features — what was added and why

### Silver

- **User shape extension — `bio` + `post_count` on every user response** (`main.py:43-48` model, `queries.py:14-27` serializer). Chosen because the A2 spec asks for richer user detail without an extra endpoint; computing `post_count` server-side via `COUNT(*) FROM posts WHERE user_id = ?` keeps the client honest (it cannot drift from the real count).
- **`PATCH /users/{username}`** (`main.py:129-139`, `queries.py:68-83`). Only `bio` is mutable; `username` and `created_at` are treated as immutable identity. Empty body `{}` is a no-op that returns 200 with the unchanged user, per PATCH semantics (see commit e5fd5a4 — we explicitly wire this path rather than 422-ing).
- **`PATCH /posts/{id}` with `X-Username` ownership enforcement** (`main.py:206-220`, `queries.py:178-198`). Three-code ownership policy — 400 missing header, 404 post not found, 403 author mismatch — chosen because each has a different meaning in the HTTP spec and collapsing them loses diagnostic signal.
- **`GET /posts?username=alice` author filter** (`main.py:172`, `queries.py:138-167`). Composable with `?q=`, `?limit=`, `?offset=`, and (gold) `?cursor=`. Unknown username returns `200 []` rather than 404 — "filter with no matches" is not the same as "endpoint not found."

### Gold

- **Cursor pagination on `GET /posts`** (`main.py:79-87` encode/decode helpers, `main.py:169-186` dispatch, `queries.py:138-167` query). Additive envelope: `?cursor=` present returns `{"posts":[...], "next_cursor": ...}`; absent keeps the bronze bare-array contract (so `?limit=` and `?offset=` still pass bronze checks).
- **Why cursor over offset:** if a row is inserted between page 1 and page 2 of an `OFFSET`-based query, offset re-counts from the top — either skipping a row (insert before current offset) or duplicating one (insert after). A cursor pinned to `last_seen_id` continues from that anchor regardless of concurrent inserts.
- **Cursor opacity:** the cursor is `base64.urlsafe_b64encode(json.dumps({"id": last_id}))`. Base64 is URL-safe and opaque to clients (discourages them from parsing or incrementing); the JSON payload inside lets us add cursor fields later (e.g. `{"id": ..., "ts": ...}`) without breaking older clients.
- **Cursor validation:** `decode_cursor` returns 422 on any parse failure — bad base64, bad JSON, missing `id` key, non-int, or negative int. README treats the cursor as a black-box string; never expose the encoding scheme in the API contract.
