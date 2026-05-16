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

THREE SECTIONS ARE MARKED 'STUDENT TODO'. You must fill them in to
complete the bronze tier. Read the assignment PDF for the exact
behavior each section should verify.
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

FAILED = 0
PASSED = 0


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
    run_silver_user_checks(c, state)
    run_silver_post_checks(c, state)
    run_silver_filter_checks(c, state)

    # ==================================================================
    # STUDENT TODO #1: DELETE /posts/{id}
    #
    # Implement run_delete_checks() below. It should verify:
    #   - DELETE on an existing post returns 204
    #   - After DELETE, GET on the same id returns 404
    #   - DELETE on a post id that doesn't exist returns 404
    #
    # state["alice_post_id"] holds a post id you created earlier.
    # Use it (or create a new one to delete). Also, pick a post id
    # that is very unlikely to exist when testing the 404 case.
    #
    # When you've implemented it, uncomment the call below.
    # ==================================================================
    run_delete_checks(c, state)

    # ==================================================================
    # STUDENT TODO #2: pagination on GET /posts
    #
    # Implement run_pagination_checks() below. It should verify:
    #   - GET /posts?limit=N returns at most N items
    #   - GET /posts?offset=K skips the first K items
    #   - GET /posts?limit=0 returns 422
    #   - GET /posts?limit=500 returns 422
    #   - GET /posts?offset=-1 returns 422
    #
    # When you've implemented it, uncomment the call below.
    # ==================================================================
    run_pagination_checks(c, state)

    # ==================================================================
    # STUDENT TODO #3: exact response field shapes
    #
    # Implement run_field_shape_checks() below. It should verify that
    # your response bodies contain EXACTLY the fields the spec lists.
    # No extras, nothing missing.
    #
    # A user object (from POST /users, GET /users/{username}, and items
    # in GET /users) has exactly {username, created_at}.
    #
    # A post object (from POST /posts, GET /posts/{id}, and items in
    # GET /posts) has exactly {id, username, message, created_at}.
    #
    # An extra field like `email`, `updated_at`, or `user_id` is a FAIL.
    # A missing field is a FAIL. You will need to compare
    # set(body.keys()) against the expected set for each shape.
    #
    # Create fresh users and posts inside this function if you want
    # isolation, or reuse state["alice_post_id"] and friends.
    #
    # When you've implemented it, uncomment the call below.
    # ==================================================================
    run_field_shape_checks(c, state)

    print()
    print(f"{PASSED} passed, {FAILED} failed")
    return 0 if FAILED == 0 else 1


def run_user_checks(c: httpx.Client, state: dict) -> None:
    r = c.post("/users", json={"username": ALICE})
    check("POST /users creates a user (201)", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        check(
            "POST /users response has exactly username, created_at, bio, post_count",
            set(body.keys()) == {"username", "created_at", "bio", "post_count"} and body["username"] == ALICE,
            detail=str(body),
        )

    r = c.post("/users", json={"username": ALICE})
    check("POST /users duplicate returns 409", r.status_code == 409, detail=f"got {r.status_code}")

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

    r = c.get(f"/users/{GHOST}")
    check(f"GET /users/{GHOST} returns 404", r.status_code == 404, detail=f"got {r.status_code}")


def run_post_checks(c: httpx.Client, state: dict) -> None:
    r = c.post("/posts", json={"message": "hello world"}, headers={"X-Username": ALICE})
    check("POST /posts with X-Username returns 201", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        expected_keys = {"id", "username", "message", "created_at", "updated_at"}
        check(
            "POST /posts response has exactly id, username, message, created_at, updated_at",
            set(body.keys()) == expected_keys,
            detail=str(body),
        )
        check("POST /posts response username matches header", body.get("username") == ALICE)
        check("POST /posts response message matches body", body.get("message") == "hello world")
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
        posts = r.json()
        check(
            "GET /posts returns a JSON array",
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
    c.post("/posts", json={"message": f"a post with {needle} in it"}, headers={"X-Username": ALICE})
    c.post("/posts", json={"message": "nothing to see"}, headers={"X-Username": ALICE})

    r = c.get("/posts", params={"q": needle})
    check(f"GET /posts?q={needle} returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        matches = r.json()
        check(
            f"GET /posts?q={needle} returns only matching posts",
            all(needle in p.get("message", "") for p in matches) and len(matches) >= 1,
            detail=str(matches),
        )


def run_delete_checks(c: httpx.Client, state: dict) -> None:
    # Create a fresh post specifically for deletion testing.
    r = c.post("/posts", json={"message": "delete me"}, headers={"X-Username": ALICE})
    assert r.status_code == 201, f"setup: could not create post to delete (got {r.status_code})"
    doomed_id = r.json()["id"]

    # DELETE on an existing post returns 204.
    r = c.delete(f"/posts/{doomed_id}")
    check("DELETE /posts/{id} returns 204", r.status_code == 204, detail=f"got {r.status_code}")

    # After DELETE, GET on the same id returns 404.
    r = c.get(f"/posts/{doomed_id}")
    check("GET /posts/{id} after DELETE returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # DELETE on a post id that doesn't exist returns 404.
    r = c.delete("/posts/99999999")
    check("DELETE /posts/99999999 (nonexistent) returns 404", r.status_code == 404, detail=f"got {r.status_code}")


def run_pagination_checks(c: httpx.Client, state: dict) -> None:
    # GET /posts?limit=N returns at most N items.
    r = c.get("/posts", params={"limit": 1})
    check(
        "GET /posts?limit=1 returns at most 1 item",
        r.status_code == 200 and isinstance(r.json(), list) and len(r.json()) <= 1,
        detail=f"status={r.status_code}, count={len(r.json()) if r.status_code == 200 else 'N/A'}",
    )

    # GET /posts?offset=K skips the first K items.
    all_posts = c.get("/posts", params={"limit": 200}).json()
    if len(all_posts) >= 2:
        offset_posts = c.get("/posts", params={"limit": 200, "offset": 1}).json()
        check(
            "GET /posts?offset=1 skips the first item",
            len(offset_posts) == len(all_posts) - 1,
            detail=f"all={len(all_posts)}, offset_1={len(offset_posts)}",
        )
    else:
        check("GET /posts?offset=K skips items (skipped, not enough posts)", True)

    # GET /posts?limit=0 returns 422.
    r = c.get("/posts", params={"limit": 0})
    check("GET /posts?limit=0 returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # GET /posts?limit=500 returns 422.
    r = c.get("/posts", params={"limit": 500})
    check("GET /posts?limit=500 returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # GET /posts?offset=-1 returns 422.
    r = c.get("/posts", params={"offset": -1})
    check("GET /posts?offset=-1 returns 422", r.status_code == 422, detail=f"got {r.status_code}")


def run_field_shape_checks(c: httpx.Client, state: dict) -> None:
    user_keys = {"username", "created_at", "bio", "post_count"}
    post_keys = {"id", "username", "message", "created_at", "updated_at"}

    # Create a fresh user and post for isolation.
    shape_user = f"shape_{RUN}"
    r = c.post("/users", json={"username": shape_user})
    if r.status_code == 201:
        body = r.json()
        check(
            "POST /users fields are exactly {username, created_at, bio, post_count}",
            set(body.keys()) == user_keys,
            detail=f"got {set(body.keys())}",
        )

    # GET /users/{username} shape.
    r = c.get(f"/users/{shape_user}")
    if r.status_code == 200:
        body = r.json()
        check(
            "GET /users/{username} fields are exactly {username, created_at, bio, post_count}",
            set(body.keys()) == user_keys,
            detail=f"got {set(body.keys())}",
        )

    # GET /users list item shape.
    r = c.get("/users")
    if r.status_code == 200:
        items = r.json()
        if items:
            check(
                "GET /users list item fields are exactly {username, created_at, bio, post_count}",
                set(items[0].keys()) == user_keys,
                detail=f"got {set(items[0].keys())}",
            )

    # POST /posts shape.
    r = c.post("/posts", json={"message": "shape test"}, headers={"X-Username": shape_user})
    if r.status_code == 201:
        body = r.json()
        check(
            "POST /posts fields are exactly {id, username, message, created_at, updated_at}",
            set(body.keys()) == post_keys,
            detail=f"got {set(body.keys())}",
        )
        shape_post_id = body["id"]

        # GET /posts/{id} shape.
        r = c.get(f"/posts/{shape_post_id}")
        if r.status_code == 200:
            body = r.json()
            check(
                "GET /posts/{id} fields are exactly {id, username, message, created_at, updated_at}",
                set(body.keys()) == post_keys,
                detail=f"got {set(body.keys())}",
            )

    # GET /posts list item shape.
    r = c.get("/posts")
    if r.status_code == 200:
        items = r.json()
        if items:
            check(
                "GET /posts list item fields are exactly {id, username, message, created_at, updated_at}",
                set(items[0].keys()) == post_keys,
                detail=f"got {set(items[0].keys())}",
            )


def run_silver_user_checks(c: httpx.Client, state: dict) -> None:
    """Silver: bio + post_count on user responses, PATCH /users/{username}."""
    sil_user = f"sil_{RUN}"

    # POST /users with bio sets bio in response.
    r = c.post("/users", json={"username": sil_user, "bio": "hello bio"})
    check("POST /users with bio returns 201", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        check(
            "POST /users with bio stores and returns bio",
            body.get("bio") == "hello bio",
            detail=str(body),
        )
        check(
            "POST /users returns post_count=0 for new user",
            body.get("post_count") == 0,
            detail=str(body),
        )

    # POST /users with oversized bio returns 422.
    r = c.post("/users", json={"username": f"big_{RUN}", "bio": "x" * 201})
    check("POST /users with 201-char bio returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # POST a couple of posts, then verify post_count reflects them.
    c.post("/posts", json={"message": "one"}, headers={"X-Username": sil_user})
    c.post("/posts", json={"message": "two"}, headers={"X-Username": sil_user})
    r = c.get(f"/users/{sil_user}")
    if r.status_code == 200:
        check(
            f"GET /users/{sil_user} post_count reflects 2 posts",
            r.json().get("post_count") == 2,
            detail=str(r.json()),
        )

    # PATCH /users/{username} updates bio.
    r = c.patch(f"/users/{sil_user}", json={"bio": "updated bio"})
    check(f"PATCH /users/{sil_user} returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        body = r.json()
        check(
            "PATCH /users/{username} response bio is updated",
            body.get("bio") == "updated bio",
            detail=str(body),
        )
        check(
            "PATCH /users/{username} preserves post_count",
            body.get("post_count") == 2,
            detail=str(body),
        )

    # PATCH /users on nonexistent user returns 404.
    r = c.patch(f"/users/{GHOST}", json={"bio": "nope"})
    check(f"PATCH /users/{GHOST} returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # PATCH /users with oversized bio returns 422.
    r = c.patch(f"/users/{sil_user}", json={"bio": "x" * 201})
    check("PATCH /users/{username} 201-char bio returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    state["sil_user"] = sil_user


def run_silver_post_checks(c: httpx.Client, state: dict) -> None:
    """Silver: PATCH /posts/{id} with author-only ownership, updated_at."""
    author = state.get("sil_user", ALICE)

    # Create a post to edit.
    r = c.post("/posts", json={"message": "original"}, headers={"X-Username": author})
    assert r.status_code == 201, f"setup failed (got {r.status_code})"
    body = r.json()
    pid = body["id"]
    check(
        "New post has updated_at = null",
        body.get("updated_at") is None,
        detail=str(body),
    )

    # Author can PATCH their own post.
    r = c.patch(f"/posts/{pid}", json={"message": "edited"}, headers={"X-Username": author})
    check(f"PATCH /posts/{pid} by author returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        body = r.json()
        check(
            "PATCH /posts/{id} response has exactly id, username, message, created_at, updated_at",
            set(body.keys()) == {"id", "username", "message", "created_at", "updated_at"},
            detail=str(body),
        )
        check("PATCH /posts/{id} message is updated", body.get("message") == "edited", detail=str(body))
        check("PATCH /posts/{id} updated_at is not null", body.get("updated_at") is not None, detail=str(body))

    # Non-author gets 403.
    r = c.patch(f"/posts/{pid}", json={"message": "hijack"}, headers={"X-Username": BOB})
    check(f"PATCH /posts/{pid} by non-author returns 403", r.status_code == 403, detail=f"got {r.status_code}")

    # Missing X-Username returns 400.
    r = c.patch(f"/posts/{pid}", json={"message": "anon"})
    check("PATCH /posts/{id} without X-Username returns 400", r.status_code == 400, detail=f"got {r.status_code}")

    # Nonexistent post returns 404.
    r = c.patch("/posts/99999999", json={"message": "ghost edit"}, headers={"X-Username": author})
    check("PATCH /posts/99999999 returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # Empty message returns 422.
    r = c.patch(f"/posts/{pid}", json={"message": ""}, headers={"X-Username": author})
    check("PATCH /posts/{id} empty message returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # Oversized message returns 422.
    r = c.patch(f"/posts/{pid}", json={"message": "x" * 501}, headers={"X-Username": author})
    check("PATCH /posts/{id} 501-char message returns 422", r.status_code == 422, detail=f"got {r.status_code}")


def run_silver_filter_checks(c: httpx.Client, state: dict) -> None:
    """Silver: GET /posts?username=alice filter."""
    author = state.get("sil_user", ALICE)

    r = c.get("/posts", params={"username": author})
    check(
        f"GET /posts?username={author} returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 200:
        posts = r.json()
        check(
            f"GET /posts?username={author} returns only that user's posts",
            all(p.get("username") == author for p in posts) and len(posts) >= 1,
            detail=f"count={len(posts)}",
        )

    # Composable with q.
    tag = f"silvertag_{RUN}"
    c.post("/posts", json={"message": f"has {tag}"}, headers={"X-Username": author})
    c.post("/posts", json={"message": "unrelated"}, headers={"X-Username": author})
    r = c.get("/posts", params={"username": author, "q": tag})
    check(
        f"GET /posts?username={author}&q={tag} is composable",
        r.status_code == 200
        and all(p.get("username") == author and tag in p.get("message", "") for p in r.json())
        and len(r.json()) >= 1,
        detail=f"status={r.status_code}",
    )

    # Unknown username returns 404.
    r = c.get("/posts", params={"username": GHOST})
    check(f"GET /posts?username={GHOST} returns 404", r.status_code == 404, detail=f"got {r.status_code}")


if __name__ == "__main__":
    sys.exit(main())
