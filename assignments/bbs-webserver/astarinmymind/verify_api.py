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
    # in GET /users) has exactly expected user fields.
    #
    # A post object (from POST /posts, GET /posts/{id}, and items in
    # GET /posts) has exactly {id, username, message, created_at, updated_at}.
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
    run_silver_checks(c, state)
    run_gold_checks(c, state)

    print()
    print(f"{PASSED} passed, {FAILED} failed")
    return 0 if FAILED == 0 else 1


def run_user_checks(c: httpx.Client, state: dict) -> None:
    r = c.post("/users", json={"username": ALICE})
    check("POST /users creates a user (201)", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        check(
            "POST /users response has exactly {username, created_at, bio, post_count}",
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

    # Boundary: exactly 3 chars is the minimum valid username
    r = c.post("/users", json={"username": f"u{RUN[:2]}"})
    check("POST /users 3-char username returns 201", r.status_code == 201, detail=f"got {r.status_code}")

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

    # Boundary: exactly 500 chars is the max valid message
    r = c.post("/posts", json={"message": "x" * 500}, headers={"X-Username": ALICE})
    check("POST /posts with 500-char message returns 201", r.status_code == 201, detail=f"got {r.status_code}")

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

    # Search with no matches returns 200 + empty array, not 404
    # @AIANDY, 200 + [] vs 404 are different semantics. 404 means "this
    # resource doesn't exist" (like /posts/99999 for a post never created).
    # An empty search result isn't a missing resource, it's a successful
    # query that found nothing. If the API returns 404 for no matches,
    # clients can't tell "bad URL" from "nothing matched your filter."
    r = c.get("/posts", params={"q": "zzz_nomatch_zzz"})
    check(
        "GET /posts?q= with no matches returns 200 + empty array",
        r.status_code == 200 and r.json() == [],
        detail=f"status {r.status_code}, body={r.json()}",
    )

    # Search for a literal % should not match everything - % is a LIKE wildcard
    # that needs to be escaped. Without escaping, ?q=% builds LIKE '%%%' which
    # matches every post in the database.
    r = c.get("/posts", params={"q": "%"})
    check(
        "GET /posts?q=% does not match all posts (LIKE wildcard escaped)",
        r.status_code == 200 and r.json() == [],
        detail=f"status {r.status_code}, count={len(r.json())}",
    )


def run_delete_checks(c: httpx.Client, state: dict) -> None:
    # Create a fresh post just for this section so we can delete it without
    # disturbing posts other checks (e.g. run_field_shape_checks) rely on.
    r = c.post("/posts", json={"message": "to be deleted"}, headers={"X-Username": ALICE})
    doomed_id = r.json()["id"]

    # DELETE on an existing post returns 204 with empty body
    # @AIANDY, 204 means "No Content" - if the endpoint accidentally returns
    # JSON on a 204, some HTTP clients will error, proxies/CDNs like nginx may
    # strip or mangle the body, and frontend fetch libraries like axios will
    # throw when calling .json() on an empty response. Works fine locally but
    # breaks in production behind a reverse proxy.
    r = c.delete(f"/posts/{doomed_id}")
    check(
        f"DELETE /posts/{doomed_id} returns 204",
        r.status_code == 204,
        detail=f"got {r.status_code}",
    )
    check(
        f"DELETE /posts/{doomed_id} has empty body",
        r.content == b"",
        detail=f"got {len(r.content)} bytes",
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
    expected_user_keys = {"username", "created_at", "bio", "post_count"}
    expected_post_keys = {"id", "username", "message", "created_at", "updated_at"}

    def check_keys(label: str, status: int, obj: dict, expected: set) -> None:
        """Check that a single response object has exactly the expected keys."""
        keys = set(obj.keys())
        check(label, keys == expected,
              detail=f"status {status}, keys={keys}")

    # --- POST /users: response should have exactly {username, created_at, bio, post_count} ---
    shape_user = f"shapeuser_{RUN}"
    r = c.post("/users", json={"username": shape_user})
    check_keys("POST /users response has exactly {username, created_at, bio, post_count}",
               r.status_code, r.json(), expected_user_keys)

    # --- GET /users/{username}: response should have exactly {username, created_at, bio, post_count} ---
    r = c.get(f"/users/{shape_user}")
    check_keys("GET /users/{username} response has exactly {username, created_at, bio, post_count}",
               r.status_code, r.json(), expected_user_keys)

    # --- GET /users: each item should have exactly {username, created_at, bio, post_count} ---
    r = c.get("/users")
    users = r.json()
    bad_keys = [set(u.keys()) for u in users if set(u.keys()) != expected_user_keys]
    check(
        "GET /users items have exactly {username, created_at, bio, post_count}",
        r.status_code == 200 and len(users) > 0 and len(bad_keys) == 0,
        detail=f"status {r.status_code}, bad items keys={bad_keys[:3]}",
    )

    # POST /posts: response should have exactly {id, username, message, created_at, updated_at}
    r = c.post("/posts", json={"message": "shape test"},
               headers={"X-Username": shape_user})
    post_body = r.json()
    check_keys("POST /posts response has exactly {id, username, message, created_at, updated_at}",
               r.status_code, post_body, expected_post_keys)

    # GET /posts/{id}: response should have exactly {id, username, message, created_at, updated_at}
    post_id = post_body["id"]
    r = c.get(f"/posts/{post_id}")
    check_keys("GET /posts/{{id}} response has exactly {id, username, message, created_at, updated_at}",
               r.status_code, r.json(), expected_post_keys)

    # GET /posts: each item should have exactly {id, username, message, created_at, updated_at}
    r = c.get("/posts")
    posts = r.json()
    bad_keys = [set(p.keys()) for p in posts if set(p.keys()) != expected_post_keys]
    check(
        "GET /posts items have exactly {id, username, message, created_at, updated_at}",
        r.status_code == 200 and len(posts) > 0 and len(bad_keys) == 0,
        detail=f"status {r.status_code}, bad items keys={bad_keys[:3]}",
    )

    # GET /users/{username}/posts: each item should have exactly {id, username, message, created_at, updated_at}
    # 
    # @AIANDY, the spec's field shape requirements only mention POST/GET /posts
    # and POST/GET /users, but /users/{username}/posts also returns post objects.
    # Added this check since it could leak extra fields through a different code path.
    r = c.get(f"/users/{shape_user}/posts")
    user_posts = r.json()
    bad_keys = [set(p.keys()) for p in user_posts if set(p.keys()) != expected_post_keys]
    check(
        "GET /users/{username}/posts items have exactly {id, username, message, created_at, updated_at}",
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


def run_silver_checks(c: httpx.Client, state: dict) -> None:
    # Create a fresh user for silver tests
    silver_user = f"silver_{RUN}"
    c.post("/users", json={"username": silver_user})

    # --- PATCH /users/{username}: update bio ---

    # PATCH with valid bio returns 200 and updated user object
    r = c.patch(f"/users/{silver_user}", json={"bio": "test bio"})
    check(
        "PATCH /users/{username} with valid bio returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )

    # Bio value is present in the PATCH response
    body = r.json()
    check(
        "PATCH /users/{username} response contains updated bio",
        body.get("bio") == "test bio",
        detail=f"got bio={body.get('bio')}",
    )

    # Bio persists - GET after PATCH shows the new bio
    r = c.get(f"/users/{silver_user}")
    check(
        "GET /users/{username} after PATCH shows updated bio",
        r.json().get("bio") == "test bio",
        detail=f"got bio={r.json().get('bio')}",
    )

    # PATCH nonexistent user returns 404
    r = c.patch(f"/users/{GHOST}", json={"bio": "nope"})
    check(
        "PATCH /users/{username} nonexistent user returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    # PATCH with bio over 200 chars returns 422
    r = c.patch(f"/users/{silver_user}", json={"bio": "a" * 201})
    check(
        "PATCH /users/{username} bio over 200 chars returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # PATCH with bio at exactly 200 chars succeeds (boundary check)
    r = c.patch(f"/users/{silver_user}", json={"bio": "b" * 200})
    check(
        "PATCH /users/{username} bio at exactly 200 chars returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )

    # --- bio and post_count value checks ---

    # New user starts with bio=null and post_count=0
    fresh_user = f"freshuser_{RUN}"
    r = c.post("/users", json={"username": fresh_user})
    body = r.json()
    check(
        "New user has bio=null",
        body.get("bio") is None,
        detail=f"got bio={body.get('bio')}",
    )
    check(
        "New user has post_count=0",
        body.get("post_count") == 0,
        detail=f"got post_count={body.get('post_count')}",
    )

    # After creating posts, post_count reflects the count
    c.post("/posts", json={"message": "post 1"}, headers={"X-Username": fresh_user})
    c.post("/posts", json={"message": "post 2"}, headers={"X-Username": fresh_user})
    r = c.get(f"/users/{fresh_user}")
    check(
        "post_count reflects number of posts",
        r.json().get("post_count") == 2,
        detail=f"got post_count={r.json().get('post_count')}",
    )

    # After deleting a post, post_count should decrease
    r = c.post("/posts", json={"message": "to delete"}, headers={"X-Username": fresh_user})
    delete_id = r.json()["id"]
    c.delete(f"/posts/{delete_id}")
    r = c.get(f"/users/{fresh_user}")
    check(
        "post_count decreases after deleting a post",
        r.json().get("post_count") == 2,
        detail=f"got post_count={r.json().get('post_count')}",
    )

    # --- PATCH /posts/{id}: edit message ---

    # Create a post to edit
    r = c.post("/posts", json={"message": "original"}, headers={"X-Username": silver_user})
    edit_post_id = r.json()["id"]

    # Fresh post should have updated_at=null before any edit
    body = r.json()
    check(
        "Fresh post has updated_at=null before any edit",
        body.get("updated_at") is None,
        detail=f"got updated_at={body.get('updated_at')}",
    )

    # PATCH with valid message returns 200
    r = c.patch(f"/posts/{edit_post_id}", json={"message": "edited"})
    check(
        "PATCH /posts/{id} with valid message returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )

    # Response contains the updated message
    body = r.json()
    check(
        "PATCH /posts/{id} response contains updated message",
        body.get("message") == "edited",
        detail=f"got message={body.get('message')}",
    )

    # Response has updated_at set (not null after edit)
    check(
        "PATCH /posts/{id} response has updated_at set",
        body.get("updated_at") is not None,
        detail=f"got updated_at={body.get('updated_at')}",
    )

    # Edit persists - GET after PATCH shows new message
    r = c.get(f"/posts/{edit_post_id}")
    check(
        "GET /posts/{id} after PATCH shows updated message",
        r.json().get("message") == "edited",
        detail=f"got message={r.json().get('message')}",
    )

    # PATCH nonexistent post returns 404
    r = c.patch("/posts/99999999", json={"message": "nope"})
    check(
        "PATCH /posts/{id} nonexistent post returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    # PATCH with empty message returns 422
    r = c.patch(f"/posts/{edit_post_id}", json={"message": ""})
    check(
        "PATCH /posts/{id} empty message returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # PATCH with oversized message returns 422
    r = c.patch(f"/posts/{edit_post_id}", json={"message": "a" * 501})
    check(
        "PATCH /posts/{id} oversized message returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # --- GET /posts?username= filter ---

    # Returns only that user's posts
    r = c.get("/posts", params={"username": silver_user})
    posts = r.json()
    check(
        "GET /posts?username= returns only that user's posts",
        r.status_code == 200
        and len(posts) > 0
        and all(p["username"] == silver_user for p in posts),
        detail=f"status {r.status_code}, count={len(posts)}",
    )

    # Returns empty array for nonexistent user (not 404)
    r = c.get("/posts", params={"username": GHOST})
    check(
        "GET /posts?username= with nonexistent user returns empty array",
        r.status_code == 200 and r.json() == [],
        detail=f"status {r.status_code}, body={r.json()}",
    )

    # Composable with ?q= - filters by both username and search term
    r = c.get("/posts", params={"username": silver_user, "q": "edited"})
    posts = r.json()
    check(
        "GET /posts?username=&q= composes both filters",
        r.status_code == 200
        and len(posts) >= 1
        and all(p["username"] == silver_user and "edited" in p["message"] for p in posts),
        detail=f"status {r.status_code}, count={len(posts)}",
    )

    # Composable with pagination - ?username= and ?limit= work together
    r = c.get("/posts", params={"username": silver_user, "limit": 1})
    posts = r.json()
    check(
        "GET /posts?username=&limit=1 composes both filters",
        r.status_code == 200
        and len(posts) <= 1
        and all(p["username"] == silver_user for p in posts),
        detail=f"status {r.status_code}, count={len(posts)}",
    )


def run_gold_checks(c: httpx.Client, state: dict) -> None:
    # --- GET /feed: N most recent posts across all users ---

    # Basic /feed returns 200 and a JSON array
    r = c.get("/feed")
    check(
        "GET /feed returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    feed = r.json()
    check(
        "GET /feed returns a JSON array",
        isinstance(feed, list),
        detail=f"got {type(feed).__name__}",
    )

    # /feed posts have the same field shape as /posts
    expected_post_keys = {"id", "username", "message", "created_at", "updated_at"}
    if len(feed) > 0:
        bad_keys = [set(p.keys()) for p in feed if set(p.keys()) != expected_post_keys]
        check(
            "GET /feed items have exactly {id, username, message, created_at, updated_at}",
            len(bad_keys) == 0,
            detail=f"bad items keys={bad_keys[:3]}",
        )

    # /feed?limit=N returns at most N items
    r = c.get("/feed", params={"limit": 2})
    check(
        "GET /feed?limit=2 returns at most 2 items",
        r.status_code == 200 and len(r.json()) <= 2,
        detail=f"status {r.status_code}, count={len(r.json())}",
    )

    # /feed?since= filters to only newer posts
    # Record a timestamp, create a post after it, then check /feed?since= only returns the new one
    from datetime import datetime
    since_ts = datetime.now().isoformat(timespec="seconds")

    gold_user = f"golduser_{RUN}"
    c.post("/users", json={"username": gold_user})
    r = c.post("/posts", json={"message": f"gold_needle_{RUN}"}, headers={"X-Username": gold_user})
    new_post_id = r.json()["id"]

    r = c.get("/feed", params={"since": since_ts})
    feed_since = r.json()
    check(
        "GET /feed?since= returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    # The post we just created should be in the filtered feed
    feed_ids = [p["id"] for p in feed_since]
    check(
        "GET /feed?since= includes post created after timestamp",
        new_post_id in feed_ids,
        detail=f"looking for {new_post_id} in {feed_ids}",
    )
    # Posts older than since should not appear - check none predate the cutoff
    check(
        "GET /feed?since= excludes posts created before timestamp",
        all(p["created_at"] >= since_ts for p in feed_since),
        detail=f"timestamps: {[p['created_at'] for p in feed_since[:5]]}",
    )


if __name__ == "__main__":
    sys.exit(main())
