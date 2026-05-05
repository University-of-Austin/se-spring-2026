# BBS Webserver

**How to run:** Install with `pip install -r requirements.txt`. Run `uvicorn main:app --port 8000` in one terminal and `python verify_api.py` in another. Delete `bbs.db` if upgrading from the bronze schema.

**Tier:** Silver.

**Design decisions:**
- Raw SQL via SQLAlchemy `text()`, kept from A1. No ORM layer needed for two tables.
- Hard delete on `DELETE /posts/{id}`, since nothing reads deleted rows.
- `PATCH /posts/{id}` is author-only. A non-author gets 403 rather than 404, since the post is publicly readable via GET.

**Schema changes from A1:** `users.joined` became `created_at NOT NULL`, `bio` was tightened to `NOT NULL DEFAULT ''`, `posts.timestamp` became `created_at`, and I added a nullable `posts.updated_at`. A1's `get_or_create_user()` was removed, so `POST /posts` with an unknown `X-Username` now returns 404.

**verify_api.py additions:** For bronze, I implemented the three TODOs. Delete verifies 204, then 404, then 404 on a ghost ID. Pagination covers the happy paths plus 422 on `limit=0`, `limit=500`, and `offset=-1`. Shape checks use exact set equality. For silver, I added bio round-trips, `post_count` incrementing, `PATCH /users` (200/404/422), `PATCH /posts` (200/403/400/404/422 with null and non-null `updated_at`), and `?username=` used alone, composed with `?q=`, and returning 404 on an unknown user.

**X-Username and auth:** The X-Username header is identity metadata, not authentication. The server trusts whatever value the client sends, so anyone can claim any username. Real authentication would verify the claim rather than trusting it: a login endpoint returns a signed token, the client resends that token on each protected request, and the server checks the signature before acting. That approach provides tamper resistance, expiration, and revocation.

**Silver additions:** `bio` and `post_count` on every user response (count via correlated subquery), `PATCH /users/{username}` for bio, `PATCH /posts/{id}` (author-only) with `updated_at` that starts null and sets on edit, and `GET /posts?username=` composable with `?q=` and pagination.
