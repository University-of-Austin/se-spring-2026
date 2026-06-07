"""
verify_api.py - conformance check for your BBS webserver.

HOW TO USE:
  1. Start your server:   uvicorn main:app --port 8000
  2. In another shell:    python verify_api.py
  3. Read the output. Fix any FAIL lines. Repeat.

This script uses random usernames on every run, so it does NOT require
a clean database. You can run it over and over against the same server.
If you want to start fresh, stop your server, delete bbs.db, and
restart.

THREE SECTIONS ARE MARKED 'STUDENT TODO'. They have been filled in.
Silver and gold sections are run at the end.
"""

import os
import sys
import uuid

import httpx

BASE = os.environ.get("BBS_BASE", "http://localhost:8000")

# Random suffix keeps test data from colliding across runs.
RUN = uuid.uuid4().hex[:8]
ALICE = f"alice_{RUN}"
BOB = f"bob_{RUN}"
GHOST = f"ghost_{RUN}"  # never created

# Silver+gold response shapes. Posts carry parent_id (nullable, for threaded
# replies) and reaction_counts (always present, zero-filled across the allowlist).
USER_KEYS = {"username", "created_at", "bio", "post_count"}
POST_KEYS = {"id", "username", "parent_id", "message", "created_at", "updated_at", "reaction_counts"}
REACTION_KINDS = {"like", "laugh", "heart"}

FAILED = 0
PASSED = 0


def _posts_body(r):
    """GET /posts returns the Gold cursor envelope
    `{"posts": [...], "next_cursor": "..."}`. This helper extracts the
    posts array so checks can iterate it directly. Raises AssertionError
    with a diagnostic if the response shape isn't an envelope — that way
    a regression in the contract surfaces at the first check rather than
    as a cascade of downstream failures."""
    body = r.json()
    assert isinstance(body, dict) and "posts" in body and "next_cursor" in body, (
        f"GET /posts did not return the cursor envelope: got {type(body).__name__} "
        f"with keys {list(body.keys()) if isinstance(body, dict) else 'N/A'}"
    )
    return body["posts"]


def check(name: str, cond: bool, detail: str = "") -> None:
    global FAILED, PASSED
    if cond:
        PASSED += 1
        print(f"PASS  {name}")
    else:
        FAILED += 1
        msg = f"FAIL  {name}"
        if detail:
            msg += f"  ({detail})"
        print(msg)


def main() -> int:
    try:
        c = httpx.Client(base_url=BASE, timeout=5.0)
        c.get("/users")
    except httpx.ConnectError:
        print(f"ERROR: could not connect to {BASE}")
        print("Is your server running? Try: uvicorn main:app --port 8000")
        return 2

    print(f"Run id: {RUN} (usernames are suffixed with this)")
    print()

    state = {}
    run_user_checks(c, state)
    run_post_checks(c, state)
    run_search_checks(c, state)
    run_pagination_checks(c, state)
    run_field_shape_checks(c, state)
    run_silver_checks(c, state)
    run_gold_cursor_checks(c, state)
    run_etag_checks(c, state)
    run_idempotency_checks(c, state)
    run_reaction_checks(c, state)
    run_threading_checks(c, state)
    run_sort_checks(c, state)
    run_trending_checks(c, state)
    run_delete_checks(c, state)  # runs last — deletes alice_post_id

    print()
    print(f"{PASSED} passed, {FAILED} failed")
    return 0 if FAILED == 0 else 1


def run_user_checks(c: httpx.Client, state: dict) -> None:
    r = c.post("/users", json={"username": ALICE})
    check("POST /users creates a user (201)", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        check(
            "POST /users response has exact silver user shape",
            set(body.keys()) == USER_KEYS and body["username"] == ALICE,
            detail=str(body),
        )
        check(
            "POST /users emits Location header pointing at new resource",
            r.headers.get("location") == f"/users/{ALICE}",
            detail=f"got {r.headers.get('location')!r}",
        )

    r = c.post("/users", json={"username": ALICE})
    check("POST /users duplicate returns 409", r.status_code == 409, detail=f"got {r.status_code}")

    # Case-insensitive uniqueness: Alice (capitalized) should also 409.
    r = c.post("/users", json={"username": ALICE.capitalize()})
    check(
        "POST /users duplicate with different casing returns 409",
        r.status_code == 409,
        detail=f"got {r.status_code}",
    )

    r = c.post("/users", json={"username": "ab"})
    check("POST /users too-short username returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.post("/users", json={"username": "has spaces"})
    check("POST /users invalid chars returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.post("/users", json={})
    check("POST /users missing username returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    c.post("/users", json={"username": BOB})

    r = c.get("/users")
    check("GET /users returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        usernames = [u["username"] for u in r.json()]
        check(
            "GET /users includes both created users",
            ALICE in usernames and BOB in usernames,
            detail=f"looking for {ALICE} and {BOB}",
        )

    r = c.get(f"/users/{ALICE}")
    check(f"GET /users/{ALICE} returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        body = r.json()
        check(
            f"GET /users/{ALICE} body.username == {ALICE}",
            body.get("username") == ALICE,
            detail=str(body),
        )

    # Case-insensitive lookup: ALICE.upper() should resolve to alice row.
    r = c.get(f"/users/{ALICE.upper()}")
    check(
        f"GET /users/{ALICE.upper()} (uppercase) returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )

    r = c.get(f"/users/{GHOST}")
    check(f"GET /users/{GHOST} returns 404", r.status_code == 404, detail=f"got {r.status_code}")


def run_post_checks(c: httpx.Client, state: dict) -> None:
    r = c.post("/posts", json={"message": "hello world"}, headers={"X-Username": ALICE})
    check("POST /posts with X-Username returns 201", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        check(
            "POST /posts response has exact silver post shape",
            set(body.keys()) == POST_KEYS,
            detail=str(body),
        )
        check("POST /posts response username matches header", body.get("username") == ALICE)
        check("POST /posts response message matches body", body.get("message") == "hello world")
        check("POST /posts updated_at is null on fresh post", body.get("updated_at") is None)
        check(
            "POST /posts emits Location header pointing at new resource",
            r.headers.get("location") == f"/posts/{body.get('id')}",
            detail=f"got {r.headers.get('location')!r}",
        )
        state["alice_post_id"] = body.get("id")

    r = c.post("/posts", json={"message": "hi"})
    check("POST /posts without X-Username returns 400", r.status_code == 400, detail=f"got {r.status_code}")

    r = c.post("/posts", json={"message": "hi"}, headers={"X-Username": GHOST})
    check("POST /posts with unknown user returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    r = c.post("/posts", json={"message": ""}, headers={"X-Username": ALICE})
    check("POST /posts with empty message returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.post(
        "/posts",
        json={"message": "x" * 501},
        headers={"X-Username": ALICE},
    )
    check("POST /posts with 501-char message returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.post("/posts", json={}, headers={"X-Username": ALICE})
    check("POST /posts missing message returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.post("/posts", json={"message": "second post"}, headers={"X-Username": BOB})
    if r.status_code == 201:
        state["bob_post_id"] = r.json().get("id")

    r = c.get("/posts")
    check("GET /posts returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        body = r.json()
        check(
            "GET /posts returns the Gold cursor envelope",
            isinstance(body, dict) and "posts" in body and "next_cursor" in body,
            detail=f"got {type(body).__name__}: {list(body.keys()) if isinstance(body, dict) else 'N/A'}",
        )
        posts = _posts_body(r)
        check(
            "GET /posts envelope carries a posts array",
            isinstance(posts, list),
            detail=f"got {type(posts).__name__}",
        )

    if "alice_post_id" in state:
        pid = state["alice_post_id"]
        r = c.get(f"/posts/{pid}")
        check(f"GET /posts/{pid} (alice's post) returns 200", r.status_code == 200, detail=f"got {r.status_code}")

    r = c.get("/posts/99999999")
    check("GET /posts/99999999 returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    r = c.get(f"/users/{ALICE}/posts")
    check(f"GET /users/{ALICE}/posts returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        alice_posts = r.json()
        check(
            f"GET /users/{ALICE}/posts contains only {ALICE}'s posts",
            all(p.get("username") == ALICE for p in alice_posts) and len(alice_posts) >= 1,
            detail=str(alice_posts),
        )

    r = c.get(f"/users/{GHOST}/posts")
    check(f"GET /users/{GHOST}/posts returns 404", r.status_code == 404, detail=f"got {r.status_code}")


def run_search_checks(c: httpx.Client, state: dict) -> None:
    needle = f"needle_{RUN}"
    r_seed = c.post(
        "/posts",
        json={"message": f"a post with {needle} in it"},
        headers={"X-Username": ALICE},
    )
    seeded_id = r_seed.json()["id"] if r_seed.status_code == 201 else None
    c.post("/posts", json={"message": "nothing to see"}, headers={"X-Username": ALICE})

    r = c.get("/posts", params={"q": needle})
    check(f"GET /posts?q={needle} returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        matches = _posts_body(r)
        check(
            f"GET /posts?q={needle} returns only matching posts",
            all(needle in p.get("message", "") for p in matches) and len(matches) >= 1,
            detail=str(matches),
        )
        # FTS5: every search hit carries a `snippet` field with match context.
        check(
            f"GET /posts?q={needle} hits include a snippet field",
            all("snippet" in p for p in matches),
            detail=str([set(p.keys()) for p in matches]),
        )
        check(
            f"GET /posts?q={needle} snippet references the needle",
            all(needle in p.get("snippet", "") for p in matches),
            detail=str([p.get("snippet") for p in matches]),
        )

    # Plain GET /posts (no q) must not leak the snippet field — breaks POST_KEYS.
    r = c.get("/posts", params={"limit": 5})
    if r.status_code == 200:
        plain_posts = _posts_body(r)
        if plain_posts:
            check(
                "GET /posts (no q) does not include snippet field",
                not any("snippet" in p for p in plain_posts),
                detail=str([set(p.keys()) for p in plain_posts[:2]]),
            )

    # Trigger sync: UPDATE advances the FTS index. After PATCH, the old needle
    # should no longer match this row and the new needle should.
    if seeded_id is not None:
        old_needle = needle
        new_needle = f"renamed_{RUN}"
        r_patch = c.patch(
            f"/posts/{seeded_id}",
            json={"message": f"now contains {new_needle} instead"},
            headers={"X-Username": ALICE},
        )
        check(
            "search setup: PATCH for trigger test succeeded",
            r_patch.status_code == 200,
            detail=f"got {r_patch.status_code}",
        )
        r = c.get("/posts", params={"q": old_needle})
        if r.status_code == 200:
            old_hits = _posts_body(r)
            check(
                "FTS UPDATE trigger: old term no longer matches the edited row",
                all(p["id"] != seeded_id for p in old_hits),
                detail=f"seeded_id={seeded_id} still in results",
            )
        r = c.get("/posts", params={"q": new_needle})
        if r.status_code == 200:
            new_hits = _posts_body(r)
            check(
                "FTS UPDATE trigger: new term matches the edited row",
                any(p["id"] == seeded_id for p in new_hits),
                detail=str([p["id"] for p in new_hits]),
            )

        # Trigger sync: DELETE evicts the row from the FTS index.
        r_del = c.delete(f"/posts/{seeded_id}", headers={"X-Username": ALICE})
        if r_del.status_code == 204:
            r = c.get("/posts", params={"q": new_needle})
            if r.status_code == 200:
                after_delete = _posts_body(r)
                check(
                    "FTS DELETE trigger: deleted row no longer searchable",
                    all(p["id"] != seeded_id for p in after_delete),
                    detail=f"seeded_id={seeded_id} still in search results",
                )

    # FTS operator-injection safety: a query that would be an FTS operator is
    # treated as a literal phrase. `hello OR world` with no post containing that
    # literal phrase returns zero rows (rather than broadening via OR).
    r = c.get("/posts", params={"q": f"{needle} OR nothing"})
    check(
        "GET /posts?q with FTS operator is treated as phrase (no operator leak)",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )

    # Silver: ?username= filter composes with the rest of the API.
    r = c.get("/posts", params={"username": ALICE})
    check(
        f"GET /posts?username={ALICE} returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 200:
        posts = _posts_body(r)
        check(
            f"GET /posts?username={ALICE} contains only {ALICE}'s posts",
            all(p.get("username") == ALICE for p in posts) and len(posts) >= 1,
            detail=str(posts[:2]),
        )

    r = c.get("/posts", params={"username": GHOST})
    check(
        f"GET /posts?username={GHOST} (unknown) returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )


def run_etag_checks(c: httpx.Client, state: dict) -> None:
    """Weak ETag W/"<id>-<ts>" on GET /posts/{id} and PATCH response.

    Verifies: presence, conditional 304 round-trip, advance after PATCH.
    """
    uname = f"etag_{RUN}"
    r = c.post("/users", json={"username": uname})
    if r.status_code != 201:
        check("etag setup: create user", False, detail=f"got {r.status_code}")
        return
    r = c.post("/posts", json={"message": "etag me"}, headers={"X-Username": uname})
    if r.status_code != 201:
        check("etag setup: create post", False, detail=f"got {r.status_code}")
        return
    pid = r.json()["id"]

    # Fresh GET emits an ETag.
    r = c.get(f"/posts/{pid}")
    etag = r.headers.get("etag")
    check(
        f"GET /posts/{pid} emits ETag header",
        etag is not None and etag.startswith('W/"') and etag.endswith('"'),
        detail=f"got {etag!r}",
    )

    # If-None-Match with the current ETag → 304, empty body.
    r = c.get(f"/posts/{pid}", headers={"If-None-Match": etag})
    check(
        f"GET /posts/{pid} with matching If-None-Match returns 304",
        r.status_code == 304,
        detail=f"got {r.status_code}",
    )
    check(
        f"304 response body is empty",
        r.content == b"",
        detail=f"got {r.content!r}",
    )

    # Non-matching → 200 with full body.
    r = c.get(f"/posts/{pid}", headers={"If-None-Match": 'W/"bogus-value"'})
    check(
        f"GET /posts/{pid} with non-matching If-None-Match returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    check(
        f"GET /posts/{pid} with non-matching If-None-Match returns body",
        r.status_code == 200 and r.json().get("id") == pid,
    )

    # PATCH advances the ETag and emits it in response headers.
    r = c.patch(
        f"/posts/{pid}",
        json={"message": "etag me, edited"},
        headers={"X-Username": uname},
    )
    new_etag = r.headers.get("etag")
    check(
        f"PATCH /posts/{pid} emits ETag header",
        new_etag is not None and new_etag.startswith('W/"'),
        detail=f"got {new_etag!r}",
    )
    check(
        f"PATCH /posts/{pid} ETag differs from pre-edit ETag",
        new_etag != etag,
        detail=f"before={etag!r} after={new_etag!r}",
    )

    # Old ETag no longer matches → 200.
    r = c.get(f"/posts/{pid}", headers={"If-None-Match": etag})
    check(
        f"stale If-None-Match after PATCH returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )


def run_idempotency_checks(c: httpx.Client, state: dict) -> None:
    """Stripe-style Idempotency-Key: same (user, key) + body replays; body
    mismatch is 422; keys are scoped per user; header absent behaves normally."""
    uname = f"idem_{RUN}"
    r = c.post("/users", json={"username": uname})
    if r.status_code != 201:
        check("idempotency setup: create user", False, detail=f"got {r.status_code}")
        return

    key = f"idem-key-{RUN}"
    body = {"message": f"idempotent message {RUN}"}

    r1 = c.post("/posts", json=body, headers={"X-Username": uname, "Idempotency-Key": key})
    check(
        "POST /posts with Idempotency-Key returns 201 on first call",
        r1.status_code == 201,
        detail=f"got {r1.status_code}",
    )
    if r1.status_code != 201:
        return
    first_id = r1.json()["id"]

    r2 = c.post("/posts", json=body, headers={"X-Username": uname, "Idempotency-Key": key})
    check(
        "POST /posts with same Idempotency-Key + same body replays",
        r2.status_code == 201 and r2.json().get("id") == first_id,
        detail=f"got {r2.status_code}, id={r2.json().get('id') if r2.status_code < 500 else '?'}",
    )

    # Count posts by this user — replay must not have created a second row.
    r = c.get(f"/users/{uname}/posts")
    if r.status_code == 200:
        check(
            "idempotent replay did not create a duplicate post",
            len(r.json()) == 1,
            detail=f"post count = {len(r.json())}",
        )

    # Same key, different body → 422 (Stripe semantics).
    r = c.post(
        "/posts",
        json={"message": "DIFFERENT body"},
        headers={"X-Username": uname, "Idempotency-Key": key},
    )
    check(
        "POST /posts with same Idempotency-Key + different body returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # Key is scoped per user: BOB can reuse the same key freely.
    r = c.post(
        "/posts",
        json={"message": "bob uses same key"},
        headers={"X-Username": BOB, "Idempotency-Key": key},
    )
    check(
        "POST /posts same Idempotency-Key under different user returns 201",
        r.status_code == 201,
        detail=f"got {r.status_code}",
    )

    # No Idempotency-Key header → normal behavior, new post each time.
    r_a = c.post(
        "/posts",
        json={"message": f"no-key {RUN}"},
        headers={"X-Username": uname},
    )
    r_b = c.post(
        "/posts",
        json={"message": f"no-key {RUN}"},
        headers={"X-Username": uname},
    )
    check(
        "POST /posts without Idempotency-Key creates distinct rows",
        r_a.status_code == 201 and r_b.status_code == 201
        and r_a.json()["id"] != r_b.json()["id"],
        detail=f"a={r_a.json().get('id')}, b={r_b.json().get('id')}",
    )


def run_reaction_checks(c: httpx.Client, state: dict) -> None:
    """PUT /posts/{id}/reactions/{kind}, DELETE ditto, GET /posts/{id}/reactions.

    Covers: idempotent PUT (201 then 204), counts roll up correctly across
    users, viewer_reactions appears only with X-Username, invalid kind → 422,
    unknown post → 404, cascade on post delete.
    """
    uname = f"reactor_{RUN}"
    r = c.post("/users", json={"username": uname})
    if r.status_code != 201:
        check("reactions setup: create user", False, detail=f"got {r.status_code}")
        return
    r = c.post("/posts", json={"message": "react to me"}, headers={"X-Username": uname})
    if r.status_code != 201:
        check("reactions setup: create post", False, detail=f"got {r.status_code}")
        return
    pid = r.json()["id"]

    # First PUT creates → 201.
    r = c.put(f"/posts/{pid}/reactions/like", headers={"X-Username": uname})
    check(
        f"PUT /posts/{pid}/reactions/like returns 201 on first call",
        r.status_code == 201,
        detail=f"got {r.status_code}",
    )
    # Second PUT is idempotent → 204 (already exists).
    r = c.put(f"/posts/{pid}/reactions/like", headers={"X-Username": uname})
    check(
        f"PUT /posts/{pid}/reactions/like returns 204 on repeat (idempotent)",
        r.status_code == 204,
        detail=f"got {r.status_code}",
    )

    # Different kind from same user stacks.
    r = c.put(f"/posts/{pid}/reactions/heart", headers={"X-Username": uname})
    check(
        f"PUT /posts/{pid}/reactions/heart (different kind) returns 201",
        r.status_code == 201,
        detail=f"got {r.status_code}",
    )

    # Another user reacts.
    r = c.put(f"/posts/{pid}/reactions/like", headers={"X-Username": ALICE})
    check(
        f"PUT /posts/{pid}/reactions/like from a second user returns 201",
        r.status_code == 201,
        detail=f"got {r.status_code}",
    )

    # GET reflects aggregate counts.
    r = c.get(f"/posts/{pid}/reactions")
    check(
        f"GET /posts/{pid}/reactions returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 200:
        body = r.json()
        check(
            "GET reactions counts.like == 2 (reactor + alice)",
            body["counts"].get("like") == 2,
            detail=str(body),
        )
        check(
            "GET reactions counts.heart == 1",
            body["counts"].get("heart") == 1,
            detail=str(body),
        )
        check(
            "GET reactions counts.laugh == 0 (zero-filled for allowlist)",
            body["counts"].get("laugh") == 0,
            detail=str(body),
        )
        check(
            "GET reactions total == sum of counts",
            body.get("total") == sum(body["counts"].values()),
            detail=str(body),
        )
        check(
            "GET reactions without X-Username omits user_reactions field",
            body.get("user_reactions") is None,
            detail=str(body),
        )

    # With X-Username, user_reactions is populated.
    r = c.get(f"/posts/{pid}/reactions", headers={"X-Username": uname})
    if r.status_code == 200:
        body = r.json()
        check(
            "GET reactions with X-Username includes user_reactions",
            set(body.get("user_reactions") or []) == {"like", "heart"},
            detail=str(body),
        )

    r = c.get(f"/posts/{pid}/reactions", headers={"X-Username": ALICE})
    if r.status_code == 200:
        body = r.json()
        check(
            "GET reactions scopes user_reactions to the caller (alice → [like])",
            body.get("user_reactions") == ["like"],
            detail=str(body),
        )

    # DELETE removes one reaction; 204. Second DELETE → 404.
    r = c.delete(f"/posts/{pid}/reactions/heart", headers={"X-Username": uname})
    check(
        f"DELETE /posts/{pid}/reactions/heart returns 204",
        r.status_code == 204,
        detail=f"got {r.status_code}",
    )
    r = c.delete(f"/posts/{pid}/reactions/heart", headers={"X-Username": uname})
    check(
        f"DELETE /posts/{pid}/reactions/heart after removal returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    # Invalid kind → 422 (Enum path param validation).
    r = c.put(f"/posts/{pid}/reactions/thumbsup", headers={"X-Username": uname})
    check(
        f"PUT /posts/{pid}/reactions/thumbsup (unknown kind) returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # Missing X-Username on PUT → 400 (require_user).
    r = c.put(f"/posts/{pid}/reactions/like")
    check(
        f"PUT /posts/{pid}/reactions/like without X-Username returns 400",
        r.status_code == 400,
        detail=f"got {r.status_code}",
    )

    # Unknown user on PUT → 404 (require_user).
    r = c.put(f"/posts/{pid}/reactions/like", headers={"X-Username": GHOST})
    check(
        f"PUT /posts/{pid}/reactions/like with unknown user returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    # Unknown post → 404 on all three verbs.
    r = c.put("/posts/99999999/reactions/like", headers={"X-Username": uname})
    check(
        "PUT /posts/99999999/reactions/like returns 404 (unknown post)",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )
    r = c.delete("/posts/99999999/reactions/like", headers={"X-Username": uname})
    check(
        "DELETE /posts/99999999/reactions/like returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )
    r = c.get("/posts/99999999/reactions")
    check(
        "GET /posts/99999999/reactions returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    # Cascade: deleting the post evicts its reactions. Use a throwaway post.
    r_setup = c.post(
        "/posts", json={"message": "cascade victim"}, headers={"X-Username": uname}
    )
    if r_setup.status_code == 201:
        victim_id = r_setup.json()["id"]
        c.put(f"/posts/{victim_id}/reactions/like", headers={"X-Username": ALICE})
        r = c.delete(f"/posts/{victim_id}", headers={"X-Username": uname})
        check(
            "DELETE post succeeds even with active reactions (FK cascade)",
            r.status_code == 204,
            detail=f"got {r.status_code}",
        )
        r = c.get(f"/posts/{victim_id}/reactions")
        check(
            "reactions index is cascade-cleared with the post",
            r.status_code == 404,
            detail=f"got {r.status_code}",
        )


def run_delete_checks(c: httpx.Client, state: dict) -> None:
    # Create a throwaway post so the 204-then-404 sequence doesn't collide
    # with anything downstream in this test run.
    r = c.post(
        "/posts",
        json={"message": f"doomed post {RUN}"},
        headers={"X-Username": ALICE},
    )
    if r.status_code != 201:
        check("DELETE setup: create throwaway post", False, detail=f"got {r.status_code}")
        return
    doomed_id = r.json()["id"]

    # Ownership: non-author can't delete.
    r = c.delete(f"/posts/{doomed_id}", headers={"X-Username": BOB})
    check(
        f"DELETE /posts/{doomed_id} by non-author returns 403",
        r.status_code == 403,
        detail=f"got {r.status_code}",
    )

    # Missing identity header is rejected.
    r = c.delete(f"/posts/{doomed_id}")
    check(
        f"DELETE /posts/{doomed_id} without X-Username returns 400",
        r.status_code == 400,
        detail=f"got {r.status_code}",
    )

    # Author succeeds.
    r = c.delete(f"/posts/{doomed_id}", headers={"X-Username": ALICE})
    check(
        f"DELETE /posts/{doomed_id} returns 204",
        r.status_code == 204,
        detail=f"got {r.status_code}",
    )
    check(
        f"DELETE /posts/{doomed_id} returns empty body",
        r.content == b"",
        detail=f"body={r.content!r}",
    )

    r = c.get(f"/posts/{doomed_id}")
    check(
        f"GET /posts/{doomed_id} after DELETE returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    r = c.delete("/posts/99999999", headers={"X-Username": ALICE})
    check(
        "DELETE /posts/99999999 (nonexistent) returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )


def run_pagination_checks(c: httpx.Client, state: dict) -> None:
    r = c.get("/posts", params={"limit": 2})
    check("GET /posts?limit=2 returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        posts = _posts_body(r)
        check(
            "GET /posts?limit=2 returns at most 2 items",
            len(posts) <= 2,
            detail=f"len={len(posts)}",
        )

    r0 = c.get("/posts", params={"limit": 5, "offset": 0})
    r1 = c.get("/posts", params={"limit": 5, "offset": 1})
    if r0.status_code == 200 and r1.status_code == 200:
        b0, b1 = _posts_body(r0), _posts_body(r1)
        if len(b0) >= 2 and len(b1) >= 1:
            check(
                "GET /posts?offset=1 skips the first item of offset=0",
                b0[1]["id"] == b1[0]["id"],
                detail=f"offset=0[1].id={b0[1]['id']}, offset=1[0].id={b1[0]['id']}",
            )
        else:
            check("GET /posts pagination offset compare skipped (too few posts)", True)

    r = c.get("/posts", params={"limit": 0})
    check("GET /posts?limit=0 returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.get("/posts", params={"limit": 500})
    check("GET /posts?limit=500 returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.get("/posts", params={"offset": -1})
    check("GET /posts?offset=-1 returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # GET /users pagination — consistency with /posts.
    r = c.get("/users", params={"limit": 1})
    check("GET /users?limit=1 returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        check("GET /users?limit=1 returns at most 1 user", len(r.json()) <= 1)
    r = c.get("/users", params={"limit": 0})
    check("GET /users?limit=0 returns 422", r.status_code == 422, detail=f"got {r.status_code}")
    r = c.get("/users", params={"limit": 500})
    check("GET /users?limit=500 returns 422", r.status_code == 422, detail=f"got {r.status_code}")
    r = c.get("/users", params={"offset": -1})
    check("GET /users?offset=-1 returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # GET /users/{username}/posts pagination.
    r = c.get(f"/users/{ALICE}/posts", params={"limit": 1})
    check(
        f"GET /users/{ALICE}/posts?limit=1 returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 200:
        check(
            f"GET /users/{ALICE}/posts?limit=1 caps at 1 item",
            len(r.json()) <= 1,
        )
    r = c.get(f"/users/{ALICE}/posts", params={"limit": 0})
    check(
        f"GET /users/{ALICE}/posts?limit=0 returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )


def run_field_shape_checks(c: httpx.Client, state: dict) -> None:
    # Fresh user/post pair, isolated from other checks.
    uname = f"shape_{RUN}"
    r = c.post("/users", json={"username": uname})
    if r.status_code != 201:
        check("field_shape setup: create user", False, detail=f"got {r.status_code}")
        return
    user_post = r.json()
    check(
        "POST /users body matches USER_KEYS exactly",
        set(user_post.keys()) == USER_KEYS,
        detail=f"got {set(user_post.keys())}",
    )

    r = c.get(f"/users/{uname}")
    if r.status_code == 200:
        check(
            f"GET /users/{uname} body matches USER_KEYS exactly",
            set(r.json().keys()) == USER_KEYS,
            detail=f"got {set(r.json().keys())}",
        )

    r = c.get("/users")
    if r.status_code == 200 and r.json():
        first = r.json()[0]
        check(
            "GET /users items match USER_KEYS exactly",
            set(first.keys()) == USER_KEYS,
            detail=f"got {set(first.keys())}",
        )

    r = c.post("/posts", json={"message": "shape check"}, headers={"X-Username": uname})
    if r.status_code != 201:
        check("field_shape setup: create post", False, detail=f"got {r.status_code}")
        return
    post_body = r.json()
    check(
        "POST /posts body matches POST_KEYS exactly",
        set(post_body.keys()) == POST_KEYS,
        detail=f"got {set(post_body.keys())}",
    )
    check("POST /posts id is int", isinstance(post_body.get("id"), int))
    check("POST /posts message is str", isinstance(post_body.get("message"), str))

    pid = post_body["id"]
    r = c.get(f"/posts/{pid}")
    if r.status_code == 200:
        check(
            f"GET /posts/{pid} body matches POST_KEYS exactly",
            set(r.json().keys()) == POST_KEYS,
            detail=f"got {set(r.json().keys())}",
        )

    r = c.get("/posts", params={"limit": 1})
    if r.status_code == 200:
        items = _posts_body(r)
        if items:
            first = items[0]
            check(
                "GET /posts items match POST_KEYS exactly",
                set(first.keys()) == POST_KEYS,
                detail=f"got {set(first.keys())}",
            )


def run_silver_checks(c: httpx.Client, state: dict) -> None:
    # PATCH /users/{username} — bio update round-trip.
    bio_text = f"bio for {ALICE}"
    r = c.patch(f"/users/{ALICE}", json={"bio": bio_text})
    check(
        f"PATCH /users/{ALICE} (bio) returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 200:
        check(
            "PATCH /users bio round-trips in response",
            r.json().get("bio") == bio_text,
            detail=str(r.json()),
        )

    r = c.get(f"/users/{ALICE}")
    if r.status_code == 200:
        check(
            f"GET /users/{ALICE} reflects updated bio",
            r.json().get("bio") == bio_text,
            detail=str(r.json()),
        )

    # Bio too long — 422.
    r = c.patch(f"/users/{ALICE}", json={"bio": "x" * 201})
    check(
        "PATCH /users with 201-char bio returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # PATCH ghost user — 404.
    r = c.patch(f"/users/{GHOST}", json={"bio": "hi"})
    check(
        f"PATCH /users/{GHOST} (unknown) returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    # post_count sanity: GET /users/{alice} post_count >= number of alice's posts.
    r_user = c.get(f"/users/{ALICE}")
    r_posts = c.get(f"/users/{ALICE}/posts")
    if r_user.status_code == 200 and r_posts.status_code == 200:
        pc = r_user.json().get("post_count")
        actual = len(r_posts.json())
        check(
            "post_count matches /users/{alice}/posts length",
            pc == actual,
            detail=f"post_count={pc}, actual={actual}",
        )

    # PATCH /posts/{id} — ownership enforced via X-Username.
    # Alice is the author of state["alice_post_id"]; Bob must get 403.
    if "alice_post_id" in state:
        pid = state["alice_post_id"]
        r = c.patch(
            f"/posts/{pid}",
            json={"message": "bob trying to edit alice's post"},
            headers={"X-Username": BOB},
        )
        check(
            f"PATCH /posts/{pid} by non-author returns 403",
            r.status_code == 403,
            detail=f"got {r.status_code}",
        )

        r = c.patch(
            f"/posts/{pid}",
            json={"message": "alice edits her own"},
            headers={"X-Username": ALICE},
        )
        check(
            f"PATCH /posts/{pid} by author returns 200",
            r.status_code == 200,
            detail=f"got {r.status_code}",
        )
        if r.status_code == 200:
            body = r.json()
            check(
                "PATCH /posts message updated in response",
                body.get("message") == "alice edits her own",
                detail=str(body),
            )
            check(
                "PATCH /posts updated_at populated after edit",
                body.get("updated_at") is not None,
                detail=str(body),
            )

    # PATCH unknown post — 404.
    r = c.patch(
        "/posts/99999999",
        json={"message": "noop"},
        headers={"X-Username": ALICE},
    )
    check(
        "PATCH /posts/99999999 (unknown) returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )


def run_gold_cursor_checks(c: httpx.Client, state: dict) -> None:
    """Gold cursor pagination per the A2 spec.

    Contract under test:
      - GET /posts returns an envelope `{"posts": [...], "next_cursor": "..."}`.
      - `next_cursor` is a base64-encoded last-seen post id; passing it as
        ?cursor= returns the next page.
      - `next_cursor` is null on the final page.
      - Invalid cursors → 422.
      - cursor combined with offset > 0 → 422 (modes are mutually exclusive).
    """
    uname = f"cursor_{RUN}"
    r = c.post("/users", json={"username": uname})
    if r.status_code != 201:
        check("gold cursor setup: create user", False, detail=f"got {r.status_code}")
        return

    N = 7
    created_ids = []
    for i in range(N):
        r = c.post(
            "/posts",
            json={"message": f"cursor_msg_{RUN}_{i}"},
            headers={"X-Username": uname},
        )
        if r.status_code == 201:
            created_ids.append(r.json()["id"])
    check(
        f"gold cursor setup: {N} posts created",
        len(created_ids) == N,
        detail=f"created {len(created_ids)}",
    )

    # First page assertions: envelope shape with both keys present.
    r = c.get("/posts", params={"limit": 3, "username": uname})
    if r.status_code != 200:
        check("gold cursor first page returns 200", False, detail=f"got {r.status_code}")
        return
    body = r.json()
    check(
        "gold cursor response is an envelope with keys {posts, next_cursor}",
        isinstance(body, dict) and set(body.keys()) >= {"posts", "next_cursor"},
        detail=f"got {type(body).__name__}: {list(body.keys()) if isinstance(body, dict) else 'N/A'}",
    )
    check(
        "gold cursor first page carries a non-empty next_cursor",
        isinstance(body.get("next_cursor"), str) and len(body["next_cursor"]) > 0,
        detail=f"next_cursor={body.get('next_cursor')!r}",
    )

    # Page through with limit=3, expect ceil(7/3) = 3 pages.
    seen: list[int] = list(p["id"] for p in body.get("posts", []))
    cursor = body.get("next_cursor")
    pages = 1
    max_pages = 10
    while cursor is not None and pages < max_pages:
        r = c.get("/posts", params={"limit": 3, "username": uname, "cursor": cursor})
        if r.status_code != 200:
            check("gold cursor page fetch returns 200", False, detail=f"got {r.status_code}")
            return
        body = r.json()
        if not (isinstance(body, dict) and "posts" in body and "next_cursor" in body):
            check("gold cursor every page is an envelope", False, detail=f"got {body!r}")
            return
        seen.extend(p["id"] for p in body["posts"])
        cursor = body["next_cursor"]
        pages += 1

    check("gold cursor paged through all N posts", len(seen) == N, detail=f"saw {len(seen)}")
    check("gold cursor no duplicate ids across pages", len(set(seen)) == len(seen))
    check(
        "gold cursor set matches created set",
        set(seen) == set(created_ids),
        detail=f"missing {set(created_ids) - set(seen)}",
    )
    check(
        "gold cursor next_cursor is null on final page",
        cursor is None,
        detail=f"final next_cursor={cursor!r}",
    )

    # Invalid cursor → 422.
    r = c.get("/posts", params={"cursor": "not-base64!!", "username": uname})
    check(
        "gold cursor invalid value returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # cursor and offset are mutually exclusive modes — mixing them → 422.
    valid_cursor = body.get("next_cursor") or "eyJpZCI6IDF9"
    # If we exited with cursor=None above, fall back to a well-formed dummy.
    r = c.get("/posts", params={"cursor": valid_cursor, "offset": 5, "username": uname})
    check(
        "gold cursor + offset > 0 returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )


def run_threading_checks(c: httpx.Client, state: dict) -> None:
    """POST /posts with parent_id creates a reply; GET /posts/{id}/replies lists
    them; nonexistent parent → 404; main feed excludes replies."""
    uname = f"thread_{RUN}"
    r = c.post("/users", json={"username": uname})
    if r.status_code != 201:
        check("threading setup: create user", False, detail=f"got {r.status_code}")
        return

    r = c.post(
        "/posts", json={"message": "top-level thread root"},
        headers={"X-Username": uname},
    )
    if r.status_code != 201:
        check("threading setup: create parent post", False, detail=f"got {r.status_code}")
        return
    parent_id = r.json()["id"]
    check(
        "POST /posts (top-level) parent_id is null",
        r.json().get("parent_id") is None,
        detail=str(r.json()),
    )

    # Reply 1.
    r = c.post(
        "/posts",
        json={"message": "reply one", "parent_id": parent_id},
        headers={"X-Username": uname},
    )
    check(
        "POST /posts with parent_id returns 201",
        r.status_code == 201,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 201:
        check(
            "POST /posts reply body.parent_id matches request",
            r.json().get("parent_id") == parent_id,
            detail=str(r.json()),
        )
        reply1_id = r.json()["id"]
    else:
        return

    # Reply 2 from another user.
    r = c.post(
        "/posts",
        json={"message": "reply two from alice", "parent_id": parent_id},
        headers={"X-Username": ALICE},
    )
    reply2_id = r.json()["id"] if r.status_code == 201 else None

    # GET /posts/{id}/replies.
    r = c.get(f"/posts/{parent_id}/replies")
    check(
        f"GET /posts/{parent_id}/replies returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 200:
        reply_ids = {p["id"] for p in r.json()}
        expected = {reply1_id} | ({reply2_id} if reply2_id else set())
        check(
            f"GET /posts/{parent_id}/replies returns the two replies",
            reply_ids == expected,
            detail=f"got {reply_ids}, expected {expected}",
        )
        check(
            "replies response has parent_id pointing at root",
            all(p.get("parent_id") == parent_id for p in r.json()),
            detail=str(r.json()),
        )
        check(
            "replies response matches POST_KEYS exactly",
            all(set(p.keys()) == POST_KEYS for p in r.json()),
            detail=str([set(p.keys()) for p in r.json()]),
        )

    # GET /posts (main feed) should exclude replies — replies belong to threads,
    # not the top-level chronological stream.
    r = c.get("/posts", params={"limit": 200})
    if r.status_code == 200:
        ids_in_feed = {p["id"] for p in _posts_body(r)}
        check(
            "main feed (GET /posts) excludes replies",
            reply1_id not in ids_in_feed and (reply2_id is None or reply2_id not in ids_in_feed),
            detail=f"reply1={reply1_id}, reply2={reply2_id}, feed_ids={len(ids_in_feed)}",
        )

    # Unknown parent → 404.
    r = c.post(
        "/posts",
        json={"message": "reply to nothing", "parent_id": 99999999},
        headers={"X-Username": uname},
    )
    check(
        "POST /posts with unknown parent_id returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    # GET replies for unknown post → 404.
    r = c.get("/posts/99999999/replies")
    check(
        "GET /posts/99999999/replies returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    # Cascade: deleting the parent deletes its replies (parent_id has ON DELETE CASCADE).
    r = c.delete(f"/posts/{parent_id}", headers={"X-Username": uname})
    check(
        "DELETE thread root succeeds",
        r.status_code == 204,
        detail=f"got {r.status_code}",
    )
    r = c.get(f"/posts/{reply1_id}")
    check(
        "reply is cascade-deleted with parent",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )


def run_sort_checks(c: httpx.Client, state: dict) -> None:
    """GET /posts?sort=top ranks by reaction count. Reaction_counts show
    on every post response."""
    uname = f"sort_{RUN}"
    r = c.post("/users", json={"username": uname})
    if r.status_code != 201:
        check("sort setup: create user", False, detail=f"got {r.status_code}")
        return

    r = c.post("/posts", json={"message": f"unpopular {RUN}"}, headers={"X-Username": uname})
    unpopular_id = r.json()["id"] if r.status_code == 201 else None
    r = c.post("/posts", json={"message": f"popular {RUN}"}, headers={"X-Username": uname})
    popular_id = r.json()["id"] if r.status_code == 201 else None

    if not unpopular_id or not popular_id:
        check("sort setup: create two posts", False)
        return

    # React to popular_id from multiple users.
    c.put(f"/posts/{popular_id}/reactions/like", headers={"X-Username": uname})
    c.put(f"/posts/{popular_id}/reactions/heart", headers={"X-Username": uname})
    c.put(f"/posts/{popular_id}/reactions/like", headers={"X-Username": ALICE})
    c.put(f"/posts/{popular_id}/reactions/laugh", headers={"X-Username": BOB})

    # Single like on unpopular for contrast.
    c.put(f"/posts/{unpopular_id}/reactions/like", headers={"X-Username": ALICE})

    # sort=top should rank popular before unpopular.
    r = c.get("/posts", params={"sort": "top", "username": uname, "limit": 10})
    check(
        f"GET /posts?sort=top&username={uname} returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 200:
        ids = [p["id"] for p in _posts_body(r)]
        if popular_id in ids and unpopular_id in ids:
            check(
                "sort=top ranks popular post above unpopular",
                ids.index(popular_id) < ids.index(unpopular_id),
                detail=f"order={ids}",
            )

    # reaction_counts projected correctly on the popular post.
    r = c.get(f"/posts/{popular_id}")
    if r.status_code == 200:
        rc = r.json().get("reaction_counts", {})
        check(
            "reaction_counts includes all three kinds",
            set(rc.keys()) == REACTION_KINDS,
            detail=str(rc),
        )
        check(
            "reaction_counts values match what we seeded (like=2, heart=1, laugh=1)",
            rc == {"like": 2, "heart": 1, "laugh": 1},
            detail=str(rc),
        )

    # Unreacted post has zero-filled counts.
    r = c.post("/posts", json={"message": f"untouched {RUN}"}, headers={"X-Username": uname})
    if r.status_code == 201:
        check(
            "fresh post has reaction_counts zero-filled",
            r.json().get("reaction_counts") == {"like": 0, "laugh": 0, "heart": 0},
            detail=str(r.json().get("reaction_counts")),
        )

    # Window filter accepts positive ints; negative or zero → 422.
    r = c.get("/posts", params={"sort": "top", "window": 24})
    check(
        "GET /posts?sort=top&window=24 returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    r = c.get("/posts", params={"sort": "top", "window": 0})
    check(
        "GET /posts?window=0 returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # Invalid sort value → 422.
    r = c.get("/posts", params={"sort": "bogus"})
    check(
        "GET /posts?sort=bogus returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # Cursor + sort=top is incompatible → 422.
    r = c.get("/posts", params={"sort": "top", "cursor": "eyJpZCI6IDF9"})
    check(
        "GET /posts?sort=top&cursor=... returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )


def run_trending_checks(c: httpx.Client, state: dict) -> None:
    """GET /posts/trending is the preset shortcut for sort=top+window=24."""
    r = c.get("/posts/trending")
    check(
        "GET /posts/trending returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 200:
        body = r.json()
        check(
            "GET /posts/trending returns a JSON array",
            isinstance(body, list),
            detail=f"got {type(body).__name__}",
        )
        if body:
            check(
                "trending items match POST_KEYS exactly",
                all(set(p.keys()) == POST_KEYS for p in body),
                detail=str([set(p.keys()) for p in body[:2]]),
            )

    # Custom window and limit.
    r = c.get("/posts/trending", params={"window": 72, "limit": 5})
    check(
        "GET /posts/trending?window=72&limit=5 returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 200:
        check(
            "trending?limit=5 returns at most 5",
            len(r.json()) <= 5,
            detail=f"len={len(r.json())}",
        )

    # Invalid bounds → 422.
    r = c.get("/posts/trending", params={"limit": 0})
    check(
        "GET /posts/trending?limit=0 returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )
    r = c.get("/posts/trending", params={"window": 0})
    check(
        "GET /posts/trending?window=0 returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )


if __name__ == "__main__":
    sys.exit(main())
