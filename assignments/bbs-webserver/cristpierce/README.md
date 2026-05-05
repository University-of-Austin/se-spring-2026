# BBS Webserver API

A RESTful BBS API built with FastAPI, wrapping a SQLite database layer. This is Assignment 2 for Software Engineering (UATX Spring 2026).

## 1. How to Run

**Dependencies:**

```bash
pip install -r requirements.txt
```

This installs `fastapi`, `uvicorn`, and `httpx`.

**Start the server:**

```bash
cd assignments/bbs-webserver/cristpierce
uvicorn main:app --port 8000
```

The database (`bbs.db`) is created automatically on first startup. No migration from A1 is needed — this is a fresh schema purpose-built for the A2 API spec.

**Run the verifier:**

```bash
python verify_api.py
```

The verifier uses random username suffixes on each run, so you do not need to delete `bbs.db` between runs.

## 2. Tier Targeted

**Gold** — all bronze and silver features, plus cursor-based pagination, boards/topics, a /feed endpoint, and reactions.

## 3. Design Decisions

- **Denormalized `username` in posts table.** Instead of storing `user_id` as a foreign key and JOINing on every read, the posts table stores `username` directly. This means every SELECT returns exactly the fields the API spec requires without any JOINs. The trade-off is that username changes would require updates in two places, but usernames are effectively immutable in this system (no rename endpoint exists). This is a common pattern in read-heavy APIs where query simplicity matters more than strict normalization.

- **Author-only PATCH enforcement.** For `PATCH /posts/{id}`, only the original author (matched via the `X-Username` header) can edit their post. A non-author receives 403 Forbidden. Even though `X-Username` is not real authentication, enforcing ownership at this layer teaches the concept of authorization and establishes the correct pattern for when real auth is added later. Allowing anyone to edit would be technically simpler but conceptually wrong — it would conflate the absence of authentication with the absence of authorization.

- **Hard delete on `DELETE /posts/{id}`.** The spec explicitly calls for hard delete, and that is what we implement. Posts are permanently removed from the database along with their associated reactions. A soft delete (marking posts as deleted but retaining the row) would be more appropriate for a production system where you want audit trails or undo capability, but the spec is clear and a hard delete is simpler to reason about.

- **Raw SQL with `text()` instead of ORM.** Consistent with A1's approach. SQLAlchemy's `text()` with parameterized `:param` syntax provides SQL injection protection without the abstraction overhead of an ORM. For a schema this small (4 tables), the ORM's value proposition (migration management, relationship loading, schema evolution) doesn't justify the added complexity. Every query is visible and auditable in the source.

- **Fresh `db.py` rather than porting from A1.** A1's schema has 11 tables with different column names (`joined` instead of `created_at`, `timestamp` instead of `created_at`, `user_id` FK instead of `username`). Rather than adapting A1's schema with rename-and-drop surgery, a fresh schema purpose-built for the A2 API spec ensures exact compliance. The column names in the database match the field names in the API responses, eliminating an entire class of field-mapping bugs.

## 4. Schema Changes from A1

A1 schema (relevant tables):

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    bio TEXT DEFAULT '',
    joined TEXT NOT NULL,          -- renamed to created_at
    avatar_ascii TEXT DEFAULT '',  -- removed (not in A2 spec)
    role TEXT DEFAULT 'user',     -- removed
    is_banned INTEGER DEFAULT 0   -- removed
);

CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,     -- changed to username TEXT
    board_id INTEGER NOT NULL,    -- changed to board TEXT (nullable)
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL,       -- renamed to created_at
    reply_to INTEGER,             -- removed (not in A2 spec)
    is_pinned INTEGER DEFAULT 0,  -- removed
    is_locked INTEGER DEFAULT 0,  -- removed
    scheduled_at TEXT,            -- removed
    has_attachment INTEGER DEFAULT 0, -- removed
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (board_id) REFERENCES boards(id)
);
```

A2 schema:

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    bio TEXT DEFAULT NULL,         -- nullable (NULL = not set, '' = explicitly empty)
    created_at TEXT NOT NULL       -- renamed from 'joined'
);

CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,        -- denormalized from user_id FK
    message TEXT NOT NULL,
    board TEXT DEFAULT NULL,       -- simplified from board_id FK
    created_at TEXT NOT NULL,      -- renamed from 'timestamp'
    updated_at TEXT DEFAULT NULL,  -- new: set on PATCH (silver)
    FOREIGN KEY (username) REFERENCES users(username)
);
```

**Key behavioral change:** A1's `get_or_create_user()` auto-created users on first post. A2 does **not** do this. `POST /posts` with an `X-Username` that doesn't exist in the database returns 404. Users must be explicitly created via `POST /users` first. This enforces a clear separation between user registration and post creation.

## 5. What I Added to verify_api.py

**TODO #1 — `run_delete_checks()`:**
- Creates a dedicated post, then DELETEs it and verifies 204
- GETs the same ID after deletion and verifies 404
- DELETEs a nonexistent post ID (99999999) and verifies 404

**TODO #2 — `run_pagination_checks()`:**
- Creates several posts, then tests `?limit=2` returns at most 2 items
- Compares full result set against `?offset=2` to verify items are skipped
- Verifies `?limit=0` returns 422 (below minimum of 1)
- Verifies `?limit=500` returns 422 (above maximum of 200)
- Verifies `?offset=-1` returns 422 (below minimum of 0)

**TODO #3 — `run_field_shape_checks()`:**
- Checks `POST /users`, `GET /users/{username}`, and `GET /users` list items all have exactly `{username, created_at, bio, post_count}`
- Checks `POST /posts`, `GET /posts/{id}`, and `GET /posts` list items all have exactly `{id, username, message, created_at, updated_at}`
- Any stray field (e.g., `board`, `id` in user responses) fails the check

**Silver assertions:**
- `bio` and `post_count` fields present in user responses
- `PATCH /users/{username}` updates bio, returns 200, persists across GET
- `PATCH /users/{ghost}` returns 404; bio > 200 chars returns 422
- `PATCH /posts/{id}` by author returns 200 with updated message and `updated_at`
- `PATCH /posts/{id}` by non-author returns 403
- `PATCH /posts/{id}` without `X-Username` returns 400
- `GET /posts?username=ALICE` filters correctly, composable with `?q=`

**Gold assertions:**
- Cursor pagination returns envelope `{posts, next_cursor}` with correct ordering
- `POST /boards` creates board (201), duplicate returns 409
- `GET /boards` lists boards, `GET /boards/{name}/posts` returns posts or 404
- `GET /feed` returns posts in reverse chronological order, respects `?limit=` and `?since=`
- `POST /posts/{id}/reactions` creates reaction (201), duplicate returns 409, nonexistent post/user returns 404
- `DELETE /posts/{id}/reactions/{username}` removes reaction (204), already-removed returns 404

**Edge cases beyond spec:**
- Verifying `post_count` is a non-negative integer
- Verifying feed ordering (first post's `created_at` >= second post's `created_at`)
- Verifying cursor pagination returns only posts with IDs less than the cursor ID

## 6. X-Username and Authentication

The `X-Username` header is **not authentication**. It is an honor-system identifier: any client can send any username, and the server will trust it. There is no password, no token, no proof of identity. A malicious client could post as anyone by simply setting `X-Username: admin`.

For real authentication, several things would need to change:

1. **A registration flow with credentials.** Users would need to provide a password (or OAuth token) when creating their account, stored as a salted hash (e.g., bcrypt), never in plaintext.

2. **A login endpoint that issues tokens.** `POST /auth/login` would accept username + password, verify the hash, and return a signed JWT (JSON Web Token) or an opaque session token. The token encodes the user's identity and has an expiration time.

3. **Token-based request authorization.** Instead of `X-Username`, clients would send `Authorization: Bearer <token>`. The server would verify the token's signature and expiration on every request, extracting the username from the token payload rather than trusting the client.

4. **HTTPS everywhere.** Without TLS, tokens travel in plaintext and can be intercepted. Real auth requires encrypted transport.

The `X-Username` pattern exists in A2 to introduce the concept that HTTP requests carry identity metadata. It is the shape of real auth without the substance. Later assignments will fill in the substance.

## 7. Gold Features — What I Added and Why

### Cursor-Based Pagination

`GET /posts?cursor=<base64>&limit=N` returns an envelope `{"posts": [...], "next_cursor": "..."}` instead of a bare array. The cursor is a base64-encoded JSON object containing the last-seen post ID (`{"id": 50}` → `eyJpZCI6IDUwfQ==`).

**Why cursors over offsets:** Offset pagination breaks under concurrent inserts. If you're viewing page 2 (`?offset=50`) and someone inserts a new post, all subsequent pages shift — you either miss a post or see a duplicate. Cursor pagination is stable because it says "give me posts older than ID 50" regardless of what was inserted after your last request. This matters for any API that serves a feed where new content arrives continuously.

### Boards/Topics

`POST /boards`, `GET /boards`, and `GET /boards/{name}/posts` add a second resource to the API. Posts can optionally belong to a board (the `board` field on posts). This introduces the concept of hierarchical resources and demonstrates how a REST API can grow beyond a flat collection.

### /feed Endpoint

`GET /feed?limit=N&since=<timestamp>` returns the N most recent posts across all users, optionally filtered to posts newer than a timestamp. This is the natural read path for a client that wants to poll for updates — call `/feed?since=<last_seen_timestamp>` to get only new content. It's distinct from `GET /posts` because it's explicitly designed for chronological consumption rather than search/browse.

### Reactions

`POST /posts/{id}/reactions` and `DELETE /posts/{id}/reactions/{username}` introduce an association table (`reactions`) and demonstrate a many-to-many relationship. Each user can react to each post once (enforced by a UNIQUE constraint). This is a common pattern in social applications and exercises a different part of the relational model than the one-to-many user→posts relationship.
