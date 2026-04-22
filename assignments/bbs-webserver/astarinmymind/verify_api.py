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
            "POST /users response has exactly username and created_at",
            set(body.keys()) == {"username", "created_at"} and body["username"] == ALICE,
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
        expected_keys = {"id", "username", "message", "created_at"}
        check(
            "POST /posts response has exactly id, username, message, created_at",
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
    # Create a fresh post just for this section so we can delete it without
    # disturbing posts other checks (e.g. run_field_shape_checks) rely on.
    r = c.post("/posts", json={"message": "to be deleted"}, headers={"X-Username": ALICE})
    doomed_id = r.json()["id"]

    # DELETE on an existing post returns 204
    r = c.delete(f"/posts/{doomed_id}")
    check(
        f"DELETE /posts/{doomed_id} returns 204",
        r.status_code == 204,
        detail=f"got {r.status_code}",
    )

    # After DELETE, GET on the same id returns 404
    r = c.get(f"/posts/{doomed_id}")
    check(
        f"GET /posts/{doomed_id} after delete returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    # DELETE on a post id that does not exist returns 404
    r = c.delete("/posts/99999999")
    check(
        "DELETE /posts/99999999 (nonexistent) returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )


def run_pagination_checks(c: httpx.Client, state: dict) -> None:
    # GET /posts?limit=N returns at most N items
    r = c.get("/posts", params={"limit": 2})
    items = r.json() if r.status_code == 200 else []
    check(
        "GET /posts?limit=2 returns at most 2 items",
        r.status_code == 200 and len(items) <= 2,
        detail=f"status {r.status_code}, got {len(items)} items",
    )

    # GET /posts?offset=K skips the first K items
    r_base = c.get("/posts", params={"limit": 10})
    baseline = r_base.json() if r_base.status_code == 200 else []
    r_off = c.get("/posts", params={"offset": 1, "limit": 10})
    offset_list = r_off.json() if r_off.status_code == 200 else []
    check(
        "GET /posts?offset=1 skips the first item",
        r_base.status_code == 200
        and r_off.status_code == 200
        and len(baseline) >= 2
        and len(offset_list) >= 1
        and offset_list[0]["id"] == baseline[1]["id"],
        detail=f"baseline_status={r_base.status_code}, offset_status={r_off.status_code}, "
               f"baseline_len={len(baseline)}, offset_len={len(offset_list)}",
    )

    # GET /posts?limit=0 returns 422
    r = c.get("/posts", params={"limit": 0})
    check("GET /posts?limit=0 returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # GET /posts?limit=500 returns 422
    r = c.get("/posts", params={"limit": 500})
    check("GET /posts?limit=500 returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # GET /posts?offset=-1 returns 422
    r = c.get("/posts", params={"offset": -1})
    check("GET /posts?offset=-1 returns 422", r.status_code == 422, detail=f"got {r.status_code}")


def run_field_shape_checks(c: httpx.Client, state: dict) -> None:
    # @AIANDY, we wrote each check inline first, noticed the repetition,
    # then pulled out check_keys(). List endpoints still loop explicitly
    # since they need to check every item.
    expected_user_keys = {"username", "created_at"}
    expected_post_keys = {"id", "username", "message", "created_at"}

    def check_keys(label: str, status: int, obj: dict, expected: set) -> None:
        """Check that a single response object has exactly the expected keys."""
        keys = set(obj.keys())
        check(label, keys == expected,
              detail=f"status {status}, keys={keys}")

    # --- POST /users: response should have exactly {username, created_at} ---
    shape_user = f"shapeuser_{RUN}"
    r = c.post("/users", json={"username": shape_user})
    check_keys("POST /users response has exactly {username, created_at}",
               r.status_code, r.json(), expected_user_keys)

    # --- GET /users/{username}: response should have exactly {username, created_at} ---
    r = c.get(f"/users/{shape_user}")
    check_keys("GET /users/{username} response has exactly {username, created_at}",
               r.status_code, r.json(), expected_user_keys)

    # --- GET /users: each item should have exactly {username, created_at} ---
    r = c.get("/users")
    users = r.json()
    bad_keys = [set(u.keys()) for u in users if set(u.keys()) != expected_user_keys]
    check(
        "GET /users items have exactly {username, created_at}",
        r.status_code == 200 and len(users) > 0 and len(bad_keys) == 0,
        detail=f"status {r.status_code}, bad items keys={bad_keys[:3]}",
    )

    # POST /posts: response should have exactly {id, username, message, created_at}
    r = c.post("/posts", json={"message": "shape test"},
               headers={"X-Username": shape_user})
    post_body = r.json()
    check_keys("POST /posts response has exactly {id, username, message, created_at}",
               r.status_code, post_body, expected_post_keys)

    # GET /posts/{id}: response should have exactly {id, username, message, created_at}
    post_id = post_body["id"]
    r = c.get(f"/posts/{post_id}")
    check_keys("GET /posts/{{id}} response has exactly {id, username, message, created_at}",
               r.status_code, r.json(), expected_post_keys)

    # GET /posts: each item should have exactly {id, username, message, created_at}
    r = c.get("/posts")
    posts = r.json()
    bad_keys = [set(p.keys()) for p in posts if set(p.keys()) != expected_post_keys]
    check(
        "GET /posts items have exactly {id, username, message, created_at}",
        r.status_code == 200 and len(posts) > 0 and len(bad_keys) == 0,
        detail=f"status {r.status_code}, bad items keys={bad_keys[:3]}",
    )

    # GET /users/{username}/posts: each item should have exactly {id, username, message, created_at}
    # 
    # @AIANDY, the spec's field shape requirements only mention POST/GET /posts
    # and POST/GET /users, but /users/{username}/posts also returns post objects.
    # Added this check since it could leak extra fields through a different code path.
    r = c.get(f"/users/{shape_user}/posts")
    user_posts = r.json()
    bad_keys = [set(p.keys()) for p in user_posts if set(p.keys()) != expected_post_keys]
    check(
        "GET /users/{username}/posts items have exactly {id, username, message, created_at}",
        r.status_code == 200 and len(user_posts) > 0 and len(bad_keys) == 0,
        detail=f"status {r.status_code}, bad items keys={bad_keys[:3]}",
    )

    # @AIANDY, we didn't add field shape checks for query param variations
    # (?q=, ?limit=, ?offset=). They all share the same query and handler as
    # GET /posts, so the plain list check above already covers the field shape.
    # Testing each variation separately would be pure duplication.

    # --- Error response shape checks ---
    # @AIANDY, your verifier checks status codes but not the error body shape.
    # 400, 404, 409 are our custom HTTPException calls, so worth verifying we
    # didn't accidentally add extra fields. 422 is FastAPI-generated and its
    # detail value is a list of validation errors rather than a string, but
    # either way the body should still have exactly {detail} as the only key.
    #
    # We only test one representative case per status code since all errors of
    # the same code go through the same HTTPException / Pydantic path.
    expected_error_keys = {"detail"}

    # 404 - nonexistent user
    r = c.get(f"/users/{GHOST}")
    check_keys("404 error body has exactly {detail} (GET /users/ghost)",
               r.status_code, r.json(), expected_error_keys)

    # 404 - nonexistent post
    r = c.get("/posts/99999999")
    check_keys("404 error body has exactly {detail} (GET /posts/99999999)",
               r.status_code, r.json(), expected_error_keys)

    # 400 - missing X-Username header
    r = c.post("/posts", json={"message": "no header"})
    check_keys("400 error body has exactly {detail} (POST /posts no header)",
               r.status_code, r.json(), expected_error_keys)

    # 409 - duplicate username
    r = c.post("/users", json={"username": shape_user})
    check_keys("409 error body has exactly {detail} (POST /users duplicate)",
               r.status_code, r.json(), expected_error_keys)

    # 422 - validation failure
    r = c.post("/users", json={"username": "ab"})
    check_keys("422 error body has exactly {detail} (POST /users too short)",
               r.status_code, r.json(), expected_error_keys)


if __name__ == "__main__":
    sys.exit(main())
