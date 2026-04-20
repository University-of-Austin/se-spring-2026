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

STUDENT EXTENSIONS (nng-source, Silver tier):
  - TODO #1/#2/#3 implemented and wired up.
  - Shipped field-shape assertions updated to match the Silver response
    shape (users gain {bio, post_count}; posts gain {updated_at}).
  - Added Silver-specific checks:
      * run_silver_user_checks (bio defaults, post_count increments,
        PATCH /users/{username}, bio over-length -> 422, PATCH unknown -> 404)
      * run_silver_post_checks (PATCH /posts/{id} sets updated_at, ownership
        policy enforced, ?username= filter works and composes with ?q=)
  - Extra edge cases beyond the spec:
      * DELETE a post that has already been deleted -> 404 (idempotency sanity)
      * GET /posts?limit=1&offset=1 sanity check that pages don't overlap
      * PATCH /posts/{id} with empty-string message -> 422 (same validator as POST)
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

# Silver response shapes (nng-source is at Silver tier).
USER_SHAPE = {"username", "created_at", "bio", "post_count"}
POST_SHAPE = {"id", "username", "message", "created_at", "updated_at"}

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

    run_delete_checks(c, state)
    run_pagination_checks(c, state)
    run_field_shape_checks(c, state)

    # Silver extensions
    run_silver_user_checks(c, state)
    run_silver_post_checks(c, state)

    print()
    print(f"{PASSED} passed, {FAILED} failed")
    return 0 if FAILED == 0 else 1


def run_user_checks(c: httpx.Client, state: dict) -> None:
    r = c.post("/users", json={"username": ALICE})
    check("POST /users creates a user (201)", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        check(
            "POST /users response matches silver user shape",
            set(body.keys()) == USER_SHAPE and body["username"] == ALICE,
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
        check(
            "POST /posts response matches silver post shape",
            set(body.keys()) == POST_SHAPE,
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


# ==========================================================================
# STUDENT TODO #1: DELETE /posts/{id}
# ==========================================================================

def run_delete_checks(c: httpx.Client, state: dict) -> None:
    # Create a dedicated post to delete so we don't wreck state for other checks.
    r = c.post("/posts", json={"message": "delete me"}, headers={"X-Username": ALICE})
    if r.status_code != 201:
        check("DELETE setup: could create post to delete", False, detail=f"got {r.status_code}")
        return
    pid = r.json()["id"]

    r = c.delete(f"/posts/{pid}")
    check("DELETE /posts/{existing} returns 204", r.status_code == 204, detail=f"got {r.status_code}")

    r = c.get(f"/posts/{pid}")
    check("GET /posts/{id} after DELETE returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # Edge case (documented): deleting an already-deleted post returns 404.
    r = c.delete(f"/posts/{pid}")
    check("DELETE /posts/{already_deleted} returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    r = c.delete("/posts/99999999")
    check("DELETE /posts/99999999 returns 404", r.status_code == 404, detail=f"got {r.status_code}")


# ==========================================================================
# STUDENT TODO #2: pagination on GET /posts
# ==========================================================================

def run_pagination_checks(c: httpx.Client, state: dict) -> None:
    # Make sure there's enough data to page through.
    for i in range(5):
        c.post(
            "/posts",
            json={"message": f"pagination probe {i} {RUN}"},
            headers={"X-Username": ALICE},
        )

    r = c.get("/posts", params={"limit": 2})
    check("GET /posts?limit=2 returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        check(
            "GET /posts?limit=2 returns at most 2 items",
            len(r.json()) <= 2,
            detail=f"got {len(r.json())}",
        )

    r1 = c.get("/posts", params={"limit": 3, "offset": 0})
    r2 = c.get("/posts", params={"limit": 3, "offset": 3})
    if r1.status_code == 200 and r2.status_code == 200:
        ids1 = {p["id"] for p in r1.json()}
        ids2 = {p["id"] for p in r2.json()}
        check(
            "GET /posts with offset=3 returns different items than offset=0",
            ids1.isdisjoint(ids2),
            detail=f"overlap: {ids1 & ids2}",
        )

    # Edge case (documented): consecutive small pages don't overlap.
    r1 = c.get("/posts", params={"limit": 1, "offset": 0})
    r2 = c.get("/posts", params={"limit": 1, "offset": 1})
    if r1.status_code == 200 and r2.status_code == 200 and r1.json() and r2.json():
        check(
            "GET /posts pages of size 1 don't overlap",
            r1.json()[0]["id"] != r2.json()[0]["id"],
            detail=f"both returned id {r1.json()[0]['id']}",
        )

    r = c.get("/posts", params={"limit": 0})
    check("GET /posts?limit=0 returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.get("/posts", params={"limit": 500})
    check("GET /posts?limit=500 returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.get("/posts", params={"offset": -1})
    check("GET /posts?offset=-1 returns 422", r.status_code == 422, detail=f"got {r.status_code}")


# ==========================================================================
# STUDENT TODO #3: exact response field shapes
# ==========================================================================

def run_field_shape_checks(c: httpx.Client, state: dict) -> None:
    # Use a fresh user and post so this check is self-contained.
    shape_user = f"shape_{RUN}"
    r = c.post("/users", json={"username": shape_user})
    if r.status_code != 201:
        check("field-shape setup: could create user", False, detail=f"got {r.status_code}")
        return

    # POST /users body
    body = r.json()
    check(
        "POST /users body has exactly the silver user shape",
        set(body.keys()) == USER_SHAPE,
        detail=f"got {set(body.keys())} expected {USER_SHAPE}",
    )

    # GET /users/{username} body
    r = c.get(f"/users/{shape_user}")
    if r.status_code == 200:
        check(
            "GET /users/{username} body has exactly the silver user shape",
            set(r.json().keys()) == USER_SHAPE,
            detail=f"got {set(r.json().keys())}",
        )

    # items in GET /users
    r = c.get("/users")
    if r.status_code == 200 and r.json():
        keys_ok = all(set(u.keys()) == USER_SHAPE for u in r.json())
        check(
            "GET /users items all have exactly the silver user shape",
            keys_ok,
            detail=f"one or more items had different keys",
        )

    # Create a post to check post shape.
    r = c.post("/posts", json={"message": "shape check"}, headers={"X-Username": shape_user})
    if r.status_code != 201:
        check("field-shape setup: could create post", False, detail=f"got {r.status_code}")
        return
    pid = r.json()["id"]

    # POST /posts body
    check(
        "POST /posts body has exactly the silver post shape",
        set(r.json().keys()) == POST_SHAPE,
        detail=f"got {set(r.json().keys())}",
    )

    # GET /posts/{id} body
    r = c.get(f"/posts/{pid}")
    if r.status_code == 200:
        check(
            "GET /posts/{id} body has exactly the silver post shape",
            set(r.json().keys()) == POST_SHAPE,
            detail=f"got {set(r.json().keys())}",
        )

    # items in GET /posts
    r = c.get("/posts", params={"limit": 5})
    if r.status_code == 200 and r.json():
        keys_ok = all(set(p.keys()) == POST_SHAPE for p in r.json())
        check(
            "GET /posts items all have exactly the silver post shape",
            keys_ok,
            detail=f"one or more items had different keys",
        )

    # items in GET /users/{username}/posts
    r = c.get(f"/users/{shape_user}/posts")
    if r.status_code == 200 and r.json():
        keys_ok = all(set(p.keys()) == POST_SHAPE for p in r.json())
        check(
            "GET /users/{username}/posts items all have exactly the silver post shape",
            keys_ok,
            detail=f"one or more items had different keys",
        )


# ==========================================================================
# SILVER CHECKS
# ==========================================================================

def run_silver_user_checks(c: httpx.Client, state: dict) -> None:
    # New user has bio == None and post_count == 0
    u = f"silveruser_{RUN}"
    r = c.post("/users", json={"username": u})
    if r.status_code != 201:
        check("silver user setup: create user", False, detail=f"got {r.status_code}")
        return
    body = r.json()
    check("new user bio is null", body.get("bio") is None, detail=str(body))
    check("new user post_count is 0", body.get("post_count") == 0, detail=str(body))

    # post_count increments after a post
    c.post("/posts", json={"message": "one"}, headers={"X-Username": u})
    c.post("/posts", json={"message": "two"}, headers={"X-Username": u})
    r = c.get(f"/users/{u}")
    check("user post_count reflects created posts", r.json().get("post_count") == 2, detail=str(r.json()))

    # PATCH /users/{username} updates bio
    r = c.patch(f"/users/{u}", json={"bio": "hello from silver"})
    check("PATCH /users/{username} returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        check("PATCH /users bio echoed in response", r.json().get("bio") == "hello from silver", detail=str(r.json()))

    # Subsequent GET reflects the bio
    r = c.get(f"/users/{u}")
    check("GET /users/{username} reflects patched bio", r.json().get("bio") == "hello from silver", detail=str(r.json()))

    # PATCH with bio > 200 chars -> 422
    r = c.patch(f"/users/{u}", json={"bio": "x" * 201})
    check("PATCH /users/{username} with 201-char bio returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # PATCH unknown user -> 404
    r = c.patch(f"/users/{GHOST}", json={"bio": "anything"})
    check("PATCH /users/{ghost} returns 404", r.status_code == 404, detail=f"got {r.status_code}")


def run_silver_post_checks(c: httpx.Client, state: dict) -> None:
    # Create a post to edit.
    r = c.post("/posts", json={"message": "original text"}, headers={"X-Username": ALICE})
    if r.status_code != 201:
        check("silver post setup: create post", False, detail=f"got {r.status_code}")
        return
    pid = r.json()["id"]
    check("new post updated_at starts as null", r.json().get("updated_at") is None, detail=str(r.json()))

    # Author can PATCH their post.
    r = c.patch(f"/posts/{pid}", json={"message": "edited text"}, headers={"X-Username": ALICE})
    check("PATCH /posts/{id} by author returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        body = r.json()
        check("PATCH /posts message is updated", body.get("message") == "edited text", detail=str(body))
        check("PATCH /posts updated_at is set", body.get("updated_at") is not None, detail=str(body))

    # Subsequent GET reflects the edit and updated_at.
    r = c.get(f"/posts/{pid}")
    if r.status_code == 200:
        check("GET /posts/{id} reflects edited message", r.json().get("message") == "edited text", detail=str(r.json()))
        check("GET /posts/{id} reflects updated_at", r.json().get("updated_at") is not None, detail=str(r.json()))

    # Non-author cannot PATCH (ownership policy: X-Username match).
    r = c.patch(f"/posts/{pid}", json={"message": "hijack"}, headers={"X-Username": BOB})
    check("PATCH /posts/{id} by non-author returns 403", r.status_code == 403, detail=f"got {r.status_code}")

    # Missing X-Username -> 400.
    r = c.patch(f"/posts/{pid}", json={"message": "anonymous edit"})
    check("PATCH /posts/{id} without X-Username returns 400", r.status_code == 400, detail=f"got {r.status_code}")

    # Unknown post -> 404.
    r = c.patch("/posts/99999999", json={"message": "ghost"}, headers={"X-Username": ALICE})
    check("PATCH /posts/99999999 returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # Edge case (documented): empty-string message on PATCH -> 422.
    r = c.patch(f"/posts/{pid}", json={"message": ""}, headers={"X-Username": ALICE})
    check("PATCH /posts/{id} with empty message returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # Filter by author.
    r = c.get("/posts", params={"username": ALICE})
    check("GET /posts?username=ALICE returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        matches = r.json()
        check(
            "GET /posts?username=ALICE returns only ALICE's posts",
            all(p.get("username") == ALICE for p in matches) and len(matches) >= 1,
            detail=f"got {[p.get('username') for p in matches]}",
        )

    # ?username= composes with ?q=.
    needle = f"compose_{RUN}"
    c.post("/posts", json={"message": f"hit {needle}"}, headers={"X-Username": ALICE})
    c.post("/posts", json={"message": f"hit {needle}"}, headers={"X-Username": BOB})
    r = c.get("/posts", params={"username": ALICE, "q": needle})
    if r.status_code == 200:
        matches = r.json()
        check(
            "GET /posts?username=ALICE&q= returns only ALICE's matching posts",
            all(p.get("username") == ALICE and needle in p.get("message", "") for p in matches)
            and len(matches) >= 1,
            detail=str(matches),
        )


if __name__ == "__main__":
    sys.exit(main())
