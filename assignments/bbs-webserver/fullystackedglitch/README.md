# BBS Webserver — fullystackedglitch

A FastAPI REST wrapper around the BBS SQLite database from Assignment 1.

## How to run

From this directory:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 8000
```

Then, in a second terminal (also with the venv activated) - I just ran in VS code terminal:

```bash
python verify_api.py
```
Some notes from Claude:

The server serves on `http://localhost:8000`. `bbs.db` is created automatically
on first run. If you want a clean slate, stop the server, `rm bbs.db`, and
restart.

**Note on migrating from A1:** I started from a fresh database rather than
migrating my A1 `bbs.db`. The schema changed (see below), and the A1 schema
included `parent_id` and `bio` defaulting to NULL — reconciling against A2's
Silver shape wasn't worth the work for this assignment. If you wanted to
migrate, you'd `ALTER TABLE users ADD COLUMN bio TEXT DEFAULT ''` and
`ALTER TABLE posts ADD COLUMN updated_at TEXT`.

## Tier targeted

**Silver.** All Bronze endpoints plus:

- `bio` and `post_count` fields on every user response
- `PATCH /users/{username}` to update a bio
- `PATCH /posts/{id}` to edit a post's message (with an author-only ownership
  policy — see design decisions)
- `GET /posts?username=X` filter, composable with `?q=`, `?limit=`, `?offset=`

## Design decisions

**REST shape: collection/item pairs, not verb endpoints.** Assignment 1 had verb-based CLI commands (`post`, `read`, `users`). A2 uses resource-based URLs: `POST /posts` creates, `GET /posts` lists, `GET /posts/{id}` fetches one, `DELETE /posts/{id}` removes. The method says the action; the URL says the noun.

**PATCH /posts ownership: author-only (403 for others).** I picked author-only because that's what every real social platform does. Sort of adding a little bit of security. Even though `X-Username` is not real auth, because I am using something close to the right policy now means that when real auth is added later, I only swap the header check for a token check — the policy doesn't change.

**Hard delete with 404 on the second call.** Deleting a missing post must return 404. There's a reasonable alternative (return 204 on repeat deletes) that handles client retries better — a retried DELETE after a lost response wouldn't see a false error. This was a Claudea (Claude idea). But the spec prioritizes semantic clarity ("404 means not found") and the real argument for either side comes down to whether clients treat DELETE 404 as failure or as idempotent success. If I was supposed to use 404 for this, I will find a way to avoid throwing 404 during idempotent DELETEs.

**Raw SQL via `text()`, not the ORM.** Kept the Assignment 1 convention. One cost: the user response computes `post_count` via a separate `SELECT COUNT(*)` query per user in `list_users()`. For a list of N users that's N+1 queries. For the scale of this assignment it's fine; a production version would join the counts in one query or denormalize the count onto the users table.

## Schema changes from Asignment #1

```sql
-- A1 schema
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    parent_id INTEGER REFERENCES posts(id)  -- A1 Silver: threads
);

-- A2 schema (changes highlighted with <-- A2 comments)
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    bio TEXT DEFAULT '',              -- <-- A2: Silver feature
    created_at TEXT NOT NULL
);

CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT                   -- <-- A2: NULL until the post is edited
);
```

**Behavioral change:** Assignment 1's `bbs_db.py post alice "hi"` silently created a user `alice` if she didn't exist. Assignment 2's `POST /posts` with `X-Username: alice` returns 404 if alice doesn't exist — users must be explicitly created first. This was an intentional break from Assignment 1: the API layer now validates identity instead of creating automatically.

## What I added to verify_api.py

- **TODO #1 — `run_delete_checks`**: the three spec bullets. For the 404 case
  I compute `max(existing_ids) + 100000` instead of hardcoding a number,
  which is robust across runs. One could also just choose a large number like a bunch of 9's, but this is unbreakable for any number of saved posts.
- **TODO #2 — `run_pagination_checks`**: the five spec bullets. For the
  "offset skips items" check, both the full request and the offset request
  use `limit=10` so the slice comparison is stable regardless of how much
  data is already in the DB.
- **TODO #3 — `run_field_shape_checks`**: six set-equality checks (POST /users,
  GET /users/{username}, items in GET /users, POST /posts, GET /posts/{id},
  items in GET /posts). These expect the Silver user shape
  `{username, created_at, bio, post_count}`, not the Bronze shape.
- **`run_silver_checks`**: eleven new assertions covering every Silver endpoint:
  PATCH user with bio, PATCH user 404, PATCH user 422 on oversized bio, PATCH
  post by author (200 + updated_at in response), PATCH post by non-author (403),
  PATCH post without header (400), PATCH post 404, and the `?username=X` filter.
- **Edit to a shipped assertion:** I changed the `run_user_checks` assertion
  `"POST /users response has exactly username and created_at"` to expect the
  Silver shape `{username, created_at, bio, post_count}`. The original assertion
  is fundamentally incompatible with Silver, since every user response includes
  `bio` and `post_count`.

## X-Username and real authentication

The `X-Username` header is not authentication — anyone can send any username and the server accepts it. If I sent `X-Username: barack_obama`, the server would cheerfully create posts as Barack Obama. The header is just "assume the client is telling the truth about who they are."

Real authentication would need two things the server doesn't currently have:
first, something the client *proves* (not just claims) — typically a session
token or JSON tokens that the server issued after a login flow; second, the server
would need to keep or verify a secret so it can tell real tokens from forgeries.
The workflow becomes: user logs in with credentials → server gives them a
signed token → client sends the token on every subsequent request → server
validates the signature before trusting the identity. The token replaces the
header; everything else about the API stays the same. PATCH's ownership check
becomes "does the token's identity match the post's author," which is the
same check I'm doing now, just against a trusted value instead of a
client-supplied one.

## Silver features in detail

**`bio` and `post_count` on user responses.** Every user endpoint
(`POST /users`, `GET /users`, `GET /users/{username}`, `PATCH /users/{username}`)
returns `{username, created_at, bio, post_count}`. `post_count` is computed on
read via `SELECT COUNT(*) FROM posts WHERE user_id = ?`.

**`PATCH /users/{username}`.** Accepts `{"bio": "..."}`, updates the bio
(max 200 chars, enforced with Pydantic's `Field(max_length=200)` → 422 on
overflow). Returns 404 if the user doesn't exist.

**`PATCH /posts/{id}`.** Accepts `{"message": "..."}`, updates the message,
sets `updated_at` to `datetime.now().isoformat()`. Response includes
`updated_at` (which is `NULL` for unedited posts). Author-only via
`X-Username` header: 400 if missing, 403 if mismatch, 404 if the post
doesn't exist.

**`GET /posts?username=X`.** Filter posts by author username. Composable with
`?q=` (substring search), `?limit=`, `?offset=`. Implemented as an optional
`AND u.username = :username` clause in the single `list_posts` query.