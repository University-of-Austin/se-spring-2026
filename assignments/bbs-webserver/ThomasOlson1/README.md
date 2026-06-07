# BBS Webserver — Thomas Olson

## Setup

Python 3.10+ required. Install dependencies:

```bash
pip install -r requirements.txt
```

`requirements.txt` contains `fastapi`, `uvicorn`, `httpx`, and `sqlalchemy`. 

## Running

Run all commands from inside `assignments/bbs-webserver/ThomasOlson1/`.

Start the server:

```bash
uvicorn main:app --port 8000
```

In another terminal, run the conformance script:

```bash
python verify_api.py
```

The verifier uses a random run id each time so usernames and board names will not collide across runs. That means the database does not need to be wiped between runs. If you want to start fresh anyway, stop the server, `rm bbs.db`, and restart.

## Tier

Gold

## Raw SQL vs ORM

I kept A1's SQLAlchemy Core + `text()` style rather than switching to the ORM. Every query is already parameterized so SQL injection does not work — my adversarial test sends `X-Username: alice'; DROP TABLE users;--` and the server just returns 404 because the parameterized query treats the whole string as a literal username lookup. A follow-up call confirms the users table is still intact. Switching to the ORM would have been rewriting working code for no meaningful benefit at this size. For a much larger project the ORM would help because it catches column typos at class definition time rather than at runtime, but that is not a real problem with only 4 tables.

## post_count: stored vs computed

A1 stores `post_count` as a column on the users table and increments it on every post, decrements it on every delete. Silver's spec says post_count should be "computed from the posts table" so I switched to running `COUNT(*)` live every time a user response is built. The reason this is good is that the column cannot drift, now that both the A1 CLI and the A2 web server insert into posts, if either one forgot to update the counter it would be wrong forever. Computing it live costs one cheap `COUNT(*)` per user response which is fine here. At a million posts it would get slower and you would want a running counter kept somewhere again, but for something this size the live count is safer and simpler.

The A1 CLI still writes to the stored column since I did not want to break the CLI. The API just ignores that column and reads the live count.

## Hard delete vs soft delete

DELETE /posts is a hard delete. The spec wants 204 on success and then 404 on GET of the same id, and hard delete gives you that for free. Soft delete (setting a `deleted_at` column and keeping the row) would mean every single read query now needs a `WHERE deleted_at IS NULL` or deleted posts leak into every list and search. It would also mean my field-shape verifier needs a new column in every post response. Not worth it for this assignment. In a real product soft delete is often better because it lets you undo mistakes and keeps stats consistent over time, but here hard delete matches the spec cleanly and does not touch the read paths.

## PATCH ownership

PATCH /posts/{id} checks `X-Username` against the post's original author. If you claim to be someone else you get 403. This is not real auth — a malicious client can just lie about the header — but it catches the actual failure mode that would come up in practice: a buggy frontend accidentally letting user A click an edit button on user B's post. The alternative was letting anyone edit any post, which the assignment said was defensible because X-Username is not auth anyway. I went with enforce because even a claim gives the server something to check, and swapping the header check for a verified token later is a one-line change.

## Path-scoped vs flat board filter

For gold I added both `GET /boards/{name}/posts` (path-scoped) and `GET /posts?board=...` (flat query param). Path-scoped is more REST-Like, boards are a resource and their posts are a sub-resource. Flat composes better with other filters. If you want "posts by alice in rust mentioning cargo" it reads more clearly as `GET /posts?board=rust&username=alice&q=cargo` than stacking query params on the nested path. Both hit the same SQL so there is not really duplicated logic, the flat endpoint just decides which WHERE clauses to add. 

The two endpoints also deliberately behave differently when the board does not exist. The path-scoped version returns 404 because you are addressing a resource that does not exist. The flat filter returns an empty list with 200 because you are filtering a stream and no posts matched. I think both of those are the right answer for what the URL is actually saying.

## Schema changes from A1

A1's schema stayed the same. Two small additive changes:

```sql
-- add a nullable updated_at to posts for silver's PATCH /posts
ALTER TABLE posts ADD COLUMN updated_at TEXT;

-- seed a default 'general' board since A2's POST /posts has no board in
-- the body, every post needs somewhere to land
INSERT OR IGNORE INTO boards (name) VALUES ('general');
```

I also removed A1's auto-create-user behavior, though that is not a schema change. In A1 if you posted as a user that did not exist, it would just create them silently. A2's spec says no — unknown username on POST /posts returns 404. This lives in the POST handler in `main.py`, not in the schema.

The A1 CLI still works against the same database. Posts I create through the web server show up in `bbs_db.py read <board>` and vice versa.

## Silver features

**User bio and post_count** — every user response now includes `bio` (max 200 chars, defaults to empty) and `post_count` (integer, computed live from the posts table). I made post_count always present with a live count rather than optional because it is cheap and clients should not have to branch on whether the key exists.

**PATCH /users/{username}** — update a user's bio. 200 on success with the full user object, 404 if the user does not exist, 422 on too-long bio or wrong type.

**PATCH /posts/{id}** — edit a post's message. Returns the post with `updated_at` set to the current timestamp. Only the original author can edit (X-Username match). 400 on missing header, 403 if the header does not match the author, 404 if the post is missing, 422 on a bad body.

**?username= filter** — `GET /posts?username=alice` returns only alice's posts. It composes with `?q=`, `?limit=`, and `?offset=` so you can stack filters like `/posts?username=alice&q=cargo&limit=10`.

One note on updated_at: it is always present in post responses, even on posts that have never been edited (null in that case). I did this rather than making the key optional because it is simpler for clients — they do not have to branch on "does the key exist" before reading it.

## Gold features

I picked **Boards** for gold since A1 already had the `boards` table and `board_id` on posts, so the schema was basically there. Most of the work was routing.

- `POST /boards` creates a board. Names are 1-40 chars with regex `[a-zA-Z0-9_-]+`. Hyphens are allowed on purpose so names feel natural. 409 on duplicate, 422 on invalid name.
- `GET /boards` lists all boards.
- `GET /boards/{name}/posts` shows posts in that board. Composes with `?q=`, `?limit=`, `?offset=`. 404 if the board does not exist.
- `POST /boards/{name}/posts` creates a post scoped to a specific board. Requires X-Username. 400 on missing header, 404 on unknown user or unknown board.
- `GET /posts?board=...` flat filter that composes with the other query params.

No X-Username is required to create a board. The reason this is fine is that we do not have real auth anyway, so gating board creation on an identity header just means "anyone who knows to set the header can make a board", which is not actually different from "anyone can make a board". If this had real auth I would probably require you to be logged in.

I also did not add DELETE /boards. Deleting a board with posts in it is a real mess. Do all the posts go away aswell or not. This would be a problem later in case a board went wrong and needed to be removed but in that case all posts from x board would most likely also need to be removed.

Post responses in gold include a new `board` field. My field-shape verifier expects this on every single post response so if an older handler is used the change it would fail immediately.

## What I added to verify_api.py

The three student TODOs plus three extra sections.

**TODO 1, delete checks** — DELETE on an existing post returns 204 with an empty body, GET on that id after returns 404, DELETE on a made-up id returns 404, and a second DELETE on the same id also returns 404. The last one is beyond spec, I wanted to confirm delete is idempotent (double-tap behavior).

**TODO 2, pagination checks** — `?limit=N` returns at most N, `?offset=K` skips the first K, and `?limit=0`, `?limit=500`, `?offset=-1` all return 422. I also added a check that `?limit=200` (the inclusive upper bound) returns 200, since `ge=1, le=200` is inclusive and I wanted to make sure that edge worked.

**TODO 3, field shape checks** — every user and post response has its key set compared against the exact expected set using `set(body.keys()) == EXPECTED`. If an extra field leaks (`email`, `user_id`, whatever) it fails. If something is missing it also fails. I used set equality rather than subset so both directions are caught. This was the one the spec specifically said to do myself rather than ask the agent, so I made sure to check every response endpoint that returns a user or a post.

**Silver checks** — bio and post_count on new users, post_count incrementing when posts are created, PATCH user in every success and error path, PATCH post in every success and error path including the 403 non-author case, and ?username= filter composing with q and limit.

**Board checks** — every board endpoint plus the flat ?board= filter, including the deliberate contract difference (path 404 on unknown vs flat 200 empty list), plus a check that POST /posts with no board path still defaults to 'general'.

**Adversarial checks** — this is extra, not required. It is where I tried to break the server. Wrong JSON types, SQL injection in the X-Username header, bad path params like `/posts/not-a-number`, bad query params like `?limit=abc`, wildcard characters in `?q=`, 1MB username, and malformed JSON bodies, etc. The main thing I wanted out of this section is that nothing returns 500 everything should be either 422 or 404. This in my opinion is great because it never shows an incompetetent user they werent the issue. 

## X-Username and auth

The X-Username header is not auth. Anyone can send any username and the server will believe it. It is a claim, not proof. I could send `X-Username: teacher` right now and the server would accept it as long as a user named teacher exists.

Silver's PATCH ownership check uses that claim to say "only the author can edit this post", which is useful for catching bugs if a buggy frontend accidentally lets user A click an edit button on user B's post, the 403 from the server stops it. But a hostile client writing their own requests can just put whatever username they want in the header.

For real auth the server needs a way to verify the identity on every request. This could be some sort of secret key this is what we had talked about earlier when dealing on the web where you have some secret key and thes erver can decrypt the otherside. This works in a two way street such that the modem cannot read everything. I think this is the path to ensure it works when you are logged in you have x secret key. 