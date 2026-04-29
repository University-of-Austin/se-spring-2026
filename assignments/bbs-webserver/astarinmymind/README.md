# BBS Webserver

## How to run

Create and activate a virtual environment, then install dependencies:

```
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Start the server:

```
uvicorn main:app --port 8000
```

Run the verifier (in a second terminal):

```
python verify_api.py
```

The database (`bbs.db`) is created automatically on first request. To start fresh, stop the server, delete `bbs.db`, and restart.

## Tier targeted

Gold.

## Design decisions

### PATCH /posts and /users does not enforce X-Username ownership

There was this feature on Signal that would notify all your contacts when you joined. Everyone hated it. And when asked about it, Moxie Marlinspike said that they try to "square the way the technology actually works with what it is that people perceive." One expects when messaging that only those two people can see it, but that's not true. And similarly, when you join Signal, anyone with your phone number can already detect you're on it. They could hit compose and see you in the list of contacts they can send messages to, or just try sending a message and see whether it goes through. The notification is just being honest about what is already possible.

Extending that philosophy here: PATCH /posts and /users does not enforce X-Username ownership. Anyone can edit any post or bio. Since X-Username is not real authentication (anyone can send any username in the header), enforcing it would be pretending the system can enforce something it can't.

Allowing open edits also makes the BBS more interesting. Others can edit your bio or messages, revealing to each person some external insight about them.

### Raw SQL over ORM

I prefer writing SQL directly. I've written a lot of SQL and am just familiar with it. That said, an ORM would reduce the boilerplate of manually building dicts from rows, which I repeat across most functions in db.py.

### Single list_posts with composable filters

GET /posts, GET /users/{username}/posts, and GET /feed all go through one `list_posts` function in db.py that builds WHERE clauses dynamically based on which filters are active (`q`, `username`, `since`, `limit`, `offset`). This avoids duplicating the same SQL across multiple endpoints.

## Schema changes from A1

```sql
-- A1
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL
);
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- A2
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL,
    bio TEXT
);
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

- Added `created_at` to users (the A2 spec requires it in every user response)
- Added `bio` to users (silver feature, optional string for user profiles)
- Renamed `timestamp` to `created_at` in posts (to match the spec's field name)
- Added `updated_at` to posts (silver feature, set when a post is edited via PATCH)
- Removed the `flair` column from A1 (not part of the A2 spec)
- Removed auto-create-user behavior from post creation. A1 would silently create a user on first post. A2 requires users to be created via POST /users first, returning 404 if the username does not exist.

## What you added to verify_api.py

**Bronze TODOs:**

- `run_delete_checks`: DELETE returns 204, GET after delete returns 404, DELETE nonexistent returns 404, and DELETE 204 has an empty body (some HTTP clients break on unexpected bodies in 204 responses)
- `run_pagination_checks`: limit returns at most N items, offset skips items, out-of-range limit/offset returns 422
- `run_field_shape_checks`: exact key checks on all user and post endpoints (POST, GET single, GET list), plus GET /users/{username}/posts (could leak extra fields through a different code path). Also checks error body shapes for 400, 404, 409, and 422 all have exactly `{detail}`. Extracted a `check_keys()` helper to avoid repetition.

**Beyond the TODOs:**

- Boundary tests: 3-char username succeeds (min valid), 500-char message succeeds (max valid), 200-char bio succeeds (max valid)
- Search with no matches returns 200 + empty array, not 404 (different semantics: "nothing matched" vs "resource not found")
- LIKE wildcard escape: searching `?q=%` should not match every post in the database
- Silver tests: PATCH /users bio (200, 404, 422, persistence), PATCH /posts message (200, 404, 422, persistence, updated_at set), bio defaults to null, post_count defaults to 0, post_count increments after creating posts, post_count decrements after deleting a post, updated_at starts null before any edit, ?username= filter, ?username= composable with ?q= and ?limit=
- Gold tests: GET /feed returns 200 and JSON array, field shapes match post objects, ?limit= works, ?since= returns only posts at or after the given timestamp

## X-Username and auth

X-Username is not authentication. Anyone can set the header to any value, so the server has no way to verify who is actually making the request. For real authentication, users would need to prove their identity, for example by logging in with a password and receiving a signed token (like a JWT) that the server can verify. The token would be cryptographically tied to the user, so unlike X-Username, it can't be faked by just typing a different value in the header.

At [Flashbots](https://docs.flashbots.net/flashbots-auction/advanced/rpc-endpoint), authentication is done via an `X-Flashbots-Signature` header. You sign the request body with your private key and send `<public key>:<signature>` in the header. The server verifies the signature against your public key, proving you hold the private key. Unlike X-Username, you can't fake it without the private key.

## Silver and gold features

I added all four silver features because I want more points. I picked /feed for gold since it was the easiest of the four options.
