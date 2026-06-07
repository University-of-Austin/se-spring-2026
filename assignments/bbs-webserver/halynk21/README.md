# BBS Webserver — Assignment 2

**Software Engineering · UATX · Spring 2026 · halynk21**

> A1's SQLite BBS grew a REST API.
> Terminal-native still works. HTTP is the new front door.

---

## Tier targeted

**Gold** — stacks bronze + silver + gold in one submission. All 93 assertions in the extended `verify_api.py` pass on a fresh `bbs.db`.

---

## How to run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. From inside this directory, start the server
uvicorn main:app --port 8000
#   (or `python -m uvicorn main:app --port 8000` if `uvicorn` is not on PATH)

# 3. In a second terminal, run the verifier
python verify_api.py
```

`bbs.db` is auto-created on first startup by the `init_db()` lifespan hook. **Run `uvicorn` from inside this directory** so `sqlite:///bbs.db` lands here rather than at the repo root — this keeps the webserver DB isolated from A1's CLI DB on purpose.

The verifier uses random username suffixes per run, so repeated runs against the same `bbs.db` are safe. To start clean: stop the server, `rm bbs.db`, restart.

---

## Design decisions

1. **Raw SQL via `sqlalchemy.text()`, not an ORM.** Matches halynk21's A1 house style. A1 was raw-SQL from day one; switching to an ORM mid-course would be a refactor disguised as progress. The Core `text()` API also makes the SQL legible in the source — anyone reviewing this can see exactly what hits the database.

2. **Schema reuse over schema rewrite.** A1's physical columns are `posts.timestamp` and `posts.edited_at`. A2's API surface says `created_at` and `updated_at`. Rather than renaming columns (and breaking the A1 CLI), every `SELECT` in `main.py` aliases them: `p.timestamp AS created_at`, `p.edited_at AS updated_at`. Zero impact on A1, clean surface for A2. The only *behavioral* change from A1 is dropping `get_or_create_user` — `POST /posts` with an unknown `X-Username` now returns 404 instead of silently creating the user, per the A2 spec.

3. **Hard delete, not soft delete.** `DELETE /posts/{id}` runs one `DELETE FROM posts WHERE id = :id`. A soft-delete tombstone would be defensible at scale (audit trails, undo windows), but this is a teaching BBS — the extra column, the extra `WHERE deleted_at IS NULL` on every read query, and the "is it really gone?" cognitive load aren't worth it here. The 404-on-unknown-id path falls out of `result.rowcount == 0`.

4. **Bronze extends into silver — shapes are a superset, not a replacement.** The silver spec adds `bio` and `post_count` to user responses and `updated_at` to post responses. Every user endpoint returns the silver shape unconditionally, and every post endpoint returns the silver shape unconditionally. The two starter assertions that hardcoded bronze-only shapes (`{username, created_at}` and `{id, username, message, created_at}`) were updated in this copy of `verify_api.py` to assert the silver-extended shapes. This is explicit in the assignment: *"You will extend [verify_api.py] to cover the rest."* Silver's expanded shape IS the extension.

5. **PATCH ownership policy: `X-Username` must match the post's author.** Non-authors get 403. Even though `X-Username` is not real authentication, modeling the policy now makes the later auth swap a header → token refactor, not a semantics refactor. The alternative — "anyone can edit anything" — would push the design debt onto future-us when real auth lands.

6. **DELETE has no `X-Username` ownership check — by design.** The spec says `DELETE /posts/{id}` is a hard delete with no mention of a required header, and `X-Username` is explicitly not authentication (anyone can forge it). Requiring a matching header on DELETE would be security theater: it adds friction without adding protection, and it's inconsistent with the spec's table. If real ownership enforcement were the goal (e.g., "only the author can delete"), the right solution is session-based auth, not a forgeable header. The PATCH policy enforces author-match because the spec invites an ownership policy choice for edits — no equivalent invitation exists for deletes.

7. **Cursor and bare-list both order by descending id.** Cursor mode uses `ORDER BY p.id DESC`; bare-list mode uses `ORDER BY p.timestamp DESC`. Under SQLite's autoincrement, row insertion order and `id` order are identical, so the two orderings agree on every real insert. The `timestamp` column stores ISO-8601 strings that sort lexicographically in the same direction as the integer id. If two posts were ever inserted with identical timestamps but different ids (possible in theory under high concurrency), the orderings could diverge by one position — but this is a teaching BBS with no concurrent writers, so the alignment is stable in practice.

8. **Reactions cascade; the PRAGMA is real.** `ON DELETE CASCADE` from `reactions.post_id → posts.id` is the first foreign key this webserver actually enforces. SQLite disables FK enforcement by default per connection, so `db.py` installs a `"connect"` event listener that runs `PRAGMA foreign_keys=ON` on every pooled connection. Without that, the CASCADE is a lie: the DDL reads as cascading, the runtime silently ignores it, and `bbs.db` accumulates orphan reactions. The verifier's GO-21 opens a direct `sqlite3` connection to the DB after a post deletion to count orphans — specifically to prove the pragma actually fires, which is otherwise unobservable through the API surface.

9. **Cursor pagination is additive, not a replacement.** When `?cursor=` is present, `GET /posts` returns the `{posts, next_cursor}` envelope. When absent, it returns a bare list with bronze's `?offset=`/`?limit=` semantics. This keeps bronze TODO #2 assertions green while layering gold cleanly. Clients opt into cursor mode by sending a cursor; there's no feature flag and no version header.

---

## Schema changes from A1

Because the webserver owns its own `bbs.db`, `init_db()` creates a clean three-table schema from scratch. No `ALTER TABLE` dance, no data migration.

```sql
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT    UNIQUE NOT NULL,
    bio        TEXT    DEFAULT '',
    created_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS posts (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL REFERENCES users(id),
    message   TEXT    NOT NULL,
    timestamp TEXT    NOT NULL,
    edited_at TEXT
);

CREATE TABLE IF NOT EXISTS reactions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    post_id    INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    kind       TEXT    NOT NULL,
    created_at TEXT    NOT NULL,
    UNIQUE(user_id, post_id, kind)
);

CREATE INDEX IF NOT EXISTS idx_posts_user_id      ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_timestamp    ON posts(timestamp);
CREATE INDEX IF NOT EXISTS idx_posts_message      ON posts(message);
CREATE INDEX IF NOT EXISTS idx_reactions_post_id  ON reactions(post_id);
CREATE INDEX IF NOT EXISTS idx_reactions_user_id  ON reactions(user_id);
```

### Column-level diff vs. A1

| Table | A1 columns | A2 columns | Delta |
|---|---|---|---|
| `users` | id, username, bio, created_at, (+ gold-tier: is_admin, is_mod, balance, total_earned, total_lost, peak_balance) | id, username, bio, created_at | A2 drops all economy / moderation columns (out of scope) |
| `posts` | id, user_id, board_id, parent_id, message, timestamp, edited_at, pinned | id, user_id, message, timestamp, edited_at | A2 drops board_id, parent_id, pinned (no boards/threads/pinning in A2) |
| `reactions` | (new in A2) | id, user_id, post_id, kind, created_at | New table — no A1 equivalent. `ON DELETE CASCADE` + composite `UNIQUE(user_id, post_id, kind)`. |

### The real change is behavioral, not structural

A1's `bbs_db.get_or_create_user(conn, username)` inserts a user on first post. A2's `POST /posts` handler does **not** auto-create — missing users return 404. There is no equivalent helper in the webserver's `db.py`. The lookup is an explicit `SELECT id FROM users WHERE username = :u`; `None` → 404.

---

## What was added to `verify_api.py`

Starting from the `main`-branch starter (`starter/assignment2/verify_api.py`), this copy adds:

| Function | Assertions | Covers |
|---|---|---|
| `run_delete_checks` (TODO #1) | 6 | DELETE returns 204; GET-after-DELETE returns 404; DELETE on nonexistent id returns 404. Uses a fresh throwaway post rather than `alice_post_id` to avoid interfering with downstream assertions. |
| `run_pagination_checks` (TODO #2) | 6 | `?limit=N` caps; `?offset=K` skips K items (compared by post id against a ground-truth `?limit=10` fetch); `?limit=0`, `?limit=500`, `?offset=-1` all return 422. |
| `run_field_shape_checks` (TODO #3) | 15 | Exact-key equality on user shape `{username, created_at, bio, post_count}` and post shape `{id, username, message, created_at, updated_at}` across POST, GET-one, and GET-list for both resources. Uses silver-extended shapes by design (see Design Decision #4). |
| `run_silver_checks` (new) | 28 | PATCH /users happy path, 404, 422, no-op; PATCH /posts happy path (including `updated_at` transition from null to non-null), 404, 403 on non-author, 400 on missing header, 422 on empty/oversized message; GET /posts?username= filter correctness; composability of `q` + `username` + `limit` + `offset`. |
| `run_gold_checks` (new) | 17 | Cursor envelope shape `{posts, next_cursor}`; silver post shape preserved inside the envelope; forward-walk with `next_cursor` matches ground-truth ordering with no duplicates; `next_cursor` is JSON `null` on the last page; invalid base64 and well-formed-base64-but-garbage-payload both return 422; bare-array behavior preserved when `cursor` is absent. |
| `run_reaction_checks` (new) | 13 | POST happy path (201 + shape check); 400/404/409/422 error paths; aggregate GET with `by_kind` counts; empty-state GET; DELETE 204 + second DELETE 404; DELETE missing header 400; GO-21 CASCADE verified via direct `sqlite3` probe after post deletion. |

Two existing starter assertions — `"POST /users response has exactly username and created_at"` and `"POST /posts response has exactly id, username, message, created_at"` — were updated to the silver-extended shapes in this copy. The assignment explicitly invites extension; since this submission targets silver/gold, shipping bronze-only shape assertions would be internally inconsistent.

### Edge cases asserted beyond the spec

- `PATCH /users/{u}` with an empty body `{}` returns 200 and leaves `bio` unchanged (PATCH semantics — omitted fields are not nulled).
- `GET /posts?username=<nonexistent>` returns 200 with an empty array, not 404. "Filter matched no rows" is a different semantic from "resource not found."
- `GET /posts` with both `cursor` and `username` composes correctly — the cursor walk stays filtered.
- The cursor payload is opaque (`base64(json({"id": <int>}))`), but changing the JSON shape later (e.g., adding a `ts` field) is backward-compatible because the decoder rejects only "missing required keys" and "non-int id," not "unexpected extra keys."
- Gold's invalid-cursor path is asserted twice: malformed base64 AND well-formed base64 whose decoded payload is not a valid cursor object. Both return 422.

---

## The X-Username header and auth

`X-Username: alice` is not authentication. Anyone can send any username, and the server takes it at face value — there is no password check, no token verification, no cryptographic binding between the request and the claimed identity. It is a *claim*, not a *credential*.

To turn this into real authentication we would need:

1. **A way to prove the claim.** A login endpoint (`POST /sessions` or similar) that accepts a password / OAuth token / passkey assertion, verifies it server-side, and issues something the client can return on subsequent requests — a short-lived JWT, a signed cookie, or an opaque session id indexed in a `sessions` table.
2. **Server-side verification per request.** Middleware that reads the credential, verifies its signature/lookup, and resolves it to a `user_id`. The resolved identity replaces `X-Username` as the authoritative source. Handlers stop trusting client-supplied usernames entirely.
3. **Password storage done right.** Never store plaintext. `argon2` or `bcrypt` with a per-user salt; the hash goes in a column the API never returns.
4. **Token hygiene.** Short expiry on access tokens, a refresh mechanism, revocation on logout. Rate limits on the login endpoint to blunt credential stuffing.
5. **Ownership policies tighten up automatically.** The PATCH policy in this submission already says *"`X-Username` must match the post's author."* When `X-Username` becomes "the authenticated user id," the same code does real authorization without further changes — that was the point of modeling the policy now.

The interesting bit: moving from `X-Username` to real auth changes the *trust model*, but the endpoint surface barely shifts. The ownership checks, the 403 responses, the per-user filtering — all of it stays. The identity substrate swaps underneath. That decoupling is why we build it this way.

---

## Silver / gold: what was added and why

### Silver

- **`bio` + `post_count` on every user response.** `bio` is a text column (already on the A1 schema). `post_count` is computed via a correlated subquery at query time — `(SELECT COUNT(*) FROM posts p WHERE p.user_id = u.id) AS post_count` — rather than maintained as a denormalized counter. At BBS scale the subquery is trivially fast; at internet scale you'd trigger-maintain or cache it, but that's a future problem.
- **`PATCH /users/{username}` (bio edit).** 200 on success, 404 on missing user, 422 on `len(bio) > 200`. Empty body is a no-op (per PATCH semantics).
- **`PATCH /posts/{id}` (message edit).** Author-match via `X-Username`; 403 on mismatch (see "Design decisions"). Sets `edited_at = now_iso()` on update, which `SELECT` exposes as `updated_at` — the canonical silver post shape gains the `updated_at: string | null` field uniformly. Unedited posts have `updated_at = null`, not a placeholder.
- **`GET /posts?username=alice` (author filter).** Composable with `?q=`, `?limit=`, `?offset=`, and `?cursor=`. Unknown username returns 200 + empty array, not 404 — "filter" ≠ "lookup."

### Gold — cursor pagination + reactions

#### Cursor pagination

Offset pagination has a concurrency problem: if a post is inserted at the head of the list between page 1 and page 2, the client sees the boundary row twice, because `offset=10` now points to the *previous* `offset=9`. At BBS scale with one user you'd never notice. At any real scale, the bug is a Heisenbug that eats the next row on every concurrent insert.

Cursor pagination anchors on the last post id the client actually saw:

```
GET /posts?cursor=<base64 of {"id": 42}>
→ {"posts": [...posts with id < 42...], "next_cursor": "..." }
```

The server's `WHERE p.id < :cursor_id ORDER BY p.id DESC LIMIT :n+1` is stable under any concurrent inserts anywhere in the table — newer rows have higher ids, so they can't leak into a page whose anchor is already fixed. The `+1` row is the "is there a next page?" probe: if we got back more than `limit` rows, there's more; otherwise `next_cursor = null` and the walk is done.

The cursor itself is `base64(json({"id": <int>}))`. Base64 is opacity theater — clients shouldn't parse it — but JSON inside means the encoding is additive: a future `{"id": 42, "since": "2026-01-01"}` cursor is a one-line decoder change, not a version bump.

#### Reactions

One emoji reaction per user-post-kind combination, enforced by `UNIQUE(user_id, post_id, kind)`. Three endpoints: `POST /posts/{id}/reactions` (201; 400 on missing header; 404 on missing post or user; 409 on duplicate; 422 on unknown kind), `DELETE /posts/{id}/reactions/{kind}` (204; 400; 404; 422), and `GET /posts/{id}/reactions` returning `{total, by_kind, reactions}`. Reaction kinds are a `Literal` at the Pydantic layer (`like`, `fire`, `laugh`, `heart`) rather than a DB `CHECK` constraint — adding a new kind is a one-line code change, not a migration.

Reactions don't leak into the post shape. `GET /posts` still returns the 5-key silver shape; clients that want counts make a separate call. This keeps pagination payloads small and defers the eager-vs-aggregate design question to whenever A3 actually needs it — adding an `?include=reactions` flag later is additive, not breaking.

### Bonus

- **`GET /`** returns `{"service": "bbs-webserver", "status": "ok", "motd": "..."}`. Not required by the spec, not asserted by the verifier. Pure pulse check — `curl localhost:8000/` and you know the server's awake.

---

## Repository layout

```
assignments/bbs-webserver/halynk21/
├── main.py           FastAPI app (routes + Pydantic models + cursor logic + reactions)
├── db.py             Engine + init_db (users, posts, reactions) + FK pragma
├── verify_api.py     Extended starter — bronze TODOs + silver + gold
├── requirements.txt  fastapi, uvicorn, httpx
├── README.md         This file
└── bbs.db            Auto-created on first startup (gitignored)
```
