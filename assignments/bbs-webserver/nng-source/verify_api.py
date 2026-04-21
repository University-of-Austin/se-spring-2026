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

STUDENT EXTENSIONS (nng-source, Silver tier + password auth):
  - TODO #1/#2/#3 implemented and wired up.
  - Shipped field-shape assertions updated to match the Silver response
    shape (users gain {bio, post_count}; posts gain {updated_at}).
  - Silver checks for bio / post_count / PATCH users + posts / ?username=
    filter / ownership policy on PATCH.
  - Password auth (beyond the A2 spec):
      * POST /users now requires `password` (>= 8 chars); short password -> 422.
      * POST /login returns {token, username}; bad password -> 401.
      * Write endpoints (POST/PATCH/DELETE on posts, PATCH on users)
        require `Authorization: Bearer <token>`; missing or stale token -> 401,
        token/identity mismatch -> 403.
      * DELETE /posts/{id} is now author-only (403 otherwise).
      * POST /logout revokes the token; subsequent writes return 401.
  - Extra edge cases beyond the A2 spec:
      * DELETE a post that has already been deleted -> 404 (idempotency).
      * GET /posts?limit=1&offset=1 sanity check that pages don't overlap.
      * PATCH /posts/{id} with empty-string message -> 422 (same validator).
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
PW_ALICE = "alice_pw_12345"
PW_BOB = "bob_pw_12345"

# Response shapes. nng-source is at Gold: posts gain `board`.
USER_SHAPE = {"username", "created_at", "bio", "post_count"}
POST_SHAPE = {"id", "username", "board", "message", "created_at", "updated_at"}
BOARD_SHAPE = {"name", "created_at", "post_count"}

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


def auth(token: str) -> dict:
    """Build an Authorization header dict for a bearer token."""
    return {"Authorization": f"Bearer {token}"}


def register_and_login(c: httpx.Client, username: str, password: str) -> str:
    """Create a user and return a session token. Fatal on failure."""
    r = c.post("/users", json={"username": username, "password": password})
    if r.status_code not in (201, 409):
        raise SystemExit(f"setup: could not create {username}: {r.status_code} {r.text}")
    r = c.post("/login", json={"username": username, "password": password})
    if r.status_code != 200 or "token" not in r.json():
        raise SystemExit(f"setup: could not log in as {username}: {r.status_code} {r.text}")
    return r.json()["token"]


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

    # Auth extensions (beyond the A2 spec)
    run_auth_checks(c, state)

    # Board (Gold) extensions
    run_board_checks(c, state)

    print()
    print(f"{PASSED} passed, {FAILED} failed")
    return 0 if FAILED == 0 else 1


def run_user_checks(c: httpx.Client, state: dict) -> None:
    r = c.post("/users", json={"username": ALICE, "password": PW_ALICE})
    check("POST /users creates a user (201)", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        check(
            "POST /users response matches silver user shape",
            set(body.keys()) == USER_SHAPE and body["username"] == ALICE,
            detail=str(body),
        )

    r = c.post("/users", json={"username": ALICE, "password": PW_ALICE})
    check("POST /users duplicate returns 409", r.status_code == 409, detail=f"got {r.status_code}")

    r = c.post("/users", json={"username": "ab", "password": PW_ALICE})
    check("POST /users too-short username returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.post("/users", json={"username": "has spaces", "password": PW_ALICE})
    check("POST /users invalid chars returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.post("/users", json={"password": PW_ALICE})
    check("POST /users missing username returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # new: password is required on create
    r = c.post("/users", json={"username": f"nopass_{RUN}"})
    check("POST /users missing password returns 422", r.status_code == 422, detail=f"got {r.status_code}")
    r = c.post("/users", json={"username": f"shortpw_{RUN}", "password": "abc"})
    check("POST /users with < 8-char password returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # log alice in, create bob, log bob in
    state["alice_token"] = register_and_login(c, ALICE, PW_ALICE)
    state["bob_token"] = register_and_login(c, BOB, PW_BOB)

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
    alice_auth = auth(state["alice_token"])
    bob_auth = auth(state["bob_token"])

    r = c.post("/posts", json={"message": "hello world"}, headers={"X-Username": ALICE, **alice_auth})
    check("POST /posts with X-Username + token returns 201", r.status_code == 201, detail=f"got {r.status_code}")
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

    r = c.post("/posts", json={"message": "hi"}, headers=alice_auth)
    check("POST /posts without X-Username returns 400", r.status_code == 400, detail=f"got {r.status_code}")

    r = c.post("/posts", json={"message": "hi"}, headers={"X-Username": GHOST, **alice_auth})
    check("POST /posts with unknown X-Username returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    r = c.post("/posts", json={"message": ""}, headers={"X-Username": ALICE, **alice_auth})
    check("POST /posts with empty message returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.post(
        "/posts",
        json={"message": "x" * 501},
        headers={"X-Username": ALICE, **alice_auth},
    )
    check("POST /posts with 501-char message returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.post("/posts", json={}, headers={"X-Username": ALICE, **alice_auth})
    check("POST /posts missing message returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.post("/posts", json={"message": "second post"}, headers={"X-Username": BOB, **bob_auth})
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
    alice_auth = auth(state["alice_token"])
    needle = f"needle_{RUN}"
    c.post("/posts", json={"message": f"a post with {needle} in it"}, headers={"X-Username": ALICE, **alice_auth})
    c.post("/posts", json={"message": "nothing to see"}, headers={"X-Username": ALICE, **alice_auth})

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
    alice_auth = auth(state["alice_token"])

    # Create a dedicated post to delete so we don't wreck state for other checks.
    r = c.post("/posts", json={"message": "delete me"}, headers={"X-Username": ALICE, **alice_auth})
    if r.status_code != 201:
        check("DELETE setup: could create post to delete", False, detail=f"got {r.status_code}")
        return
    pid = r.json()["id"]

    r = c.delete(f"/posts/{pid}", headers=alice_auth)
    check("DELETE /posts/{existing} (by author) returns 204", r.status_code == 204, detail=f"got {r.status_code}")

    r = c.get(f"/posts/{pid}")
    check("GET /posts/{id} after DELETE returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # Edge case (documented): deleting an already-deleted post returns 404.
    r = c.delete(f"/posts/{pid}", headers=alice_auth)
    check("DELETE /posts/{already_deleted} returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    r = c.delete("/posts/99999999", headers=alice_auth)
    check("DELETE /posts/99999999 returns 404", r.status_code == 404, detail=f"got {r.status_code}")


# ==========================================================================
# STUDENT TODO #2: pagination on GET /posts
# ==========================================================================

def run_pagination_checks(c: httpx.Client, state: dict) -> None:
    alice_auth = auth(state["alice_token"])

    # Make sure there's enough data to page through.
    for i in range(5):
        c.post(
            "/posts",
            json={"message": f"pagination probe {i} {RUN}"},
            headers={"X-Username": ALICE, **alice_auth},
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
    shape_user = f"shape_{RUN}"
    shape_pw = "shape_pw_12345"
    token = register_and_login(c, shape_user, shape_pw)
    auth_headers = auth(token)

    # Create fresh user specifically for shape checks; body validation of POST
    # /users return shape already runs in run_user_checks, so here we mainly
    # confirm GET shapes.
    r = c.get(f"/users/{shape_user}")
    check(
        "POST /users body has exactly the silver user shape",
        r.status_code == 200 and set(r.json().keys()) == USER_SHAPE,
        detail=f"got {r.status_code} {r.json() if r.status_code==200 else ''}",
    )

    r = c.get(f"/users/{shape_user}")
    if r.status_code == 200:
        check(
            "GET /users/{username} body has exactly the silver user shape",
            set(r.json().keys()) == USER_SHAPE,
            detail=f"got {set(r.json().keys())}",
        )

    r = c.get("/users")
    if r.status_code == 200 and r.json():
        keys_ok = all(set(u.keys()) == USER_SHAPE for u in r.json())
        check(
            "GET /users items all have exactly the silver user shape",
            keys_ok,
            detail="one or more items had different keys",
        )

    # Create a post to check post shape.
    r = c.post(
        "/posts",
        json={"message": "shape check"},
        headers={"X-Username": shape_user, **auth_headers},
    )
    if r.status_code != 201:
        check("field-shape setup: could create post", False, detail=f"got {r.status_code}")
        return
    pid = r.json()["id"]

    check(
        "POST /posts body has exactly the silver post shape",
        set(r.json().keys()) == POST_SHAPE,
        detail=f"got {set(r.json().keys())}",
    )

    r = c.get(f"/posts/{pid}")
    if r.status_code == 200:
        check(
            "GET /posts/{id} body has exactly the silver post shape",
            set(r.json().keys()) == POST_SHAPE,
            detail=f"got {set(r.json().keys())}",
        )

    r = c.get("/posts", params={"limit": 5})
    if r.status_code == 200 and r.json():
        keys_ok = all(set(p.keys()) == POST_SHAPE for p in r.json())
        check(
            "GET /posts items all have exactly the silver post shape",
            keys_ok,
            detail="one or more items had different keys",
        )

    r = c.get(f"/users/{shape_user}/posts")
    if r.status_code == 200 and r.json():
        keys_ok = all(set(p.keys()) == POST_SHAPE for p in r.json())
        check(
            "GET /users/{username}/posts items all have exactly the silver post shape",
            keys_ok,
            detail="one or more items had different keys",
        )


# ==========================================================================
# SILVER CHECKS
# ==========================================================================

def run_silver_user_checks(c: httpx.Client, state: dict) -> None:
    u = f"silveruser_{RUN}"
    pw = "silver_pw_12345"
    r = c.post("/users", json={"username": u, "password": pw})
    if r.status_code != 201:
        check("silver user setup: create user", False, detail=f"got {r.status_code}")
        return
    body = r.json()
    check("new user bio is null", body.get("bio") is None, detail=str(body))
    check("new user post_count is 0", body.get("post_count") == 0, detail=str(body))

    token = c.post("/login", json={"username": u, "password": pw}).json()["token"]
    auth_headers = auth(token)

    c.post("/posts", json={"message": "one"}, headers={"X-Username": u, **auth_headers})
    c.post("/posts", json={"message": "two"}, headers={"X-Username": u, **auth_headers})
    r = c.get(f"/users/{u}")
    check("user post_count reflects created posts", r.json().get("post_count") == 2, detail=str(r.json()))

    r = c.patch(f"/users/{u}", json={"bio": "hello from silver"}, headers=auth_headers)
    check("PATCH /users/{username} returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        check("PATCH /users bio echoed in response", r.json().get("bio") == "hello from silver", detail=str(r.json()))

    r = c.get(f"/users/{u}")
    check("GET /users/{username} reflects patched bio", r.json().get("bio") == "hello from silver", detail=str(r.json()))

    r = c.patch(f"/users/{u}", json={"bio": "x" * 201}, headers=auth_headers)
    check("PATCH /users/{username} with 201-char bio returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.patch(f"/users/{GHOST}", json={"bio": "anything"}, headers=auth_headers)
    check("PATCH /users/{ghost} returns 404", r.status_code == 404, detail=f"got {r.status_code}")


def run_silver_post_checks(c: httpx.Client, state: dict) -> None:
    alice_auth = auth(state["alice_token"])
    bob_auth = auth(state["bob_token"])

    r = c.post(
        "/posts",
        json={"message": "original text"},
        headers={"X-Username": ALICE, **alice_auth},
    )
    if r.status_code != 201:
        check("silver post setup: create post", False, detail=f"got {r.status_code}")
        return
    pid = r.json()["id"]
    check("new post updated_at starts as null", r.json().get("updated_at") is None, detail=str(r.json()))

    r = c.patch(
        f"/posts/{pid}",
        json={"message": "edited text"},
        headers={"X-Username": ALICE, **alice_auth},
    )
    check("PATCH /posts/{id} by author returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        body = r.json()
        check("PATCH /posts message is updated", body.get("message") == "edited text", detail=str(body))
        check("PATCH /posts updated_at is set", body.get("updated_at") is not None, detail=str(body))

    r = c.get(f"/posts/{pid}")
    if r.status_code == 200:
        check("GET /posts/{id} reflects edited message", r.json().get("message") == "edited text", detail=str(r.json()))
        check("GET /posts/{id} reflects updated_at", r.json().get("updated_at") is not None, detail=str(r.json()))

    # Non-author cannot PATCH (ownership policy).
    r = c.patch(
        f"/posts/{pid}",
        json={"message": "hijack"},
        headers={"X-Username": BOB, **bob_auth},
    )
    check("PATCH /posts/{id} by non-author returns 403", r.status_code == 403, detail=f"got {r.status_code}")

    r = c.patch(f"/posts/{pid}", json={"message": "anonymous edit"}, headers=alice_auth)
    check("PATCH /posts/{id} without X-Username returns 400", r.status_code == 400, detail=f"got {r.status_code}")

    r = c.patch(
        "/posts/99999999",
        json={"message": "ghost"},
        headers={"X-Username": ALICE, **alice_auth},
    )
    check("PATCH /posts/99999999 returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # Edge case: empty-string message on PATCH -> 422.
    r = c.patch(
        f"/posts/{pid}",
        json={"message": ""},
        headers={"X-Username": ALICE, **alice_auth},
    )
    check("PATCH /posts/{id} with empty message returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.get("/posts", params={"username": ALICE})
    check("GET /posts?username=ALICE returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        matches = r.json()
        check(
            "GET /posts?username=ALICE returns only ALICE's posts",
            all(p.get("username") == ALICE for p in matches) and len(matches) >= 1,
            detail=f"got {[p.get('username') for p in matches]}",
        )

    needle = f"compose_{RUN}"
    c.post("/posts", json={"message": f"hit {needle}"}, headers={"X-Username": ALICE, **alice_auth})
    c.post("/posts", json={"message": f"hit {needle}"}, headers={"X-Username": BOB, **bob_auth})
    r = c.get("/posts", params={"username": ALICE, "q": needle})
    if r.status_code == 200:
        matches = r.json()
        check(
            "GET /posts?username=ALICE&q= returns only ALICE's matching posts",
            all(p.get("username") == ALICE and needle in p.get("message", "") for p in matches)
            and len(matches) >= 1,
            detail=str(matches),
        )


# ==========================================================================
# AUTH CHECKS (beyond the A2 spec)
# ==========================================================================

def run_auth_checks(c: httpx.Client, state: dict) -> None:
    alice_auth = auth(state["alice_token"])
    bob_auth = auth(state["bob_token"])

    # POST /login happy path and 401 on wrong password
    r = c.post("/login", json={"username": ALICE, "password": "wrong-password"})
    check("POST /login wrong password returns 401", r.status_code == 401, detail=f"got {r.status_code}")
    r = c.post("/login", json={"username": GHOST, "password": "whatever"})
    check("POST /login unknown user returns 401", r.status_code == 401, detail=f"got {r.status_code}")

    # Write ops require Authorization
    r = c.post("/posts", json={"message": "anon"}, headers={"X-Username": ALICE})
    check("POST /posts without token returns 401", r.status_code == 401, detail=f"got {r.status_code}")
    r = c.post("/posts", json={"message": "bad"}, headers={"X-Username": ALICE, "Authorization": "Bearer not-a-real-token"})
    check("POST /posts with invalid token returns 401", r.status_code == 401, detail=f"got {r.status_code}")

    # Token/identity mismatch -> 403
    r = c.post("/posts", json={"message": "spoof"}, headers={"X-Username": BOB, **alice_auth})
    check("POST /posts with token != X-Username returns 403", r.status_code == 403, detail=f"got {r.status_code}")

    # PATCH user requires the session to match the path username
    r = c.patch(f"/users/{ALICE}", json={"bio": "hijack"}, headers=bob_auth)
    check("PATCH /users/{alice} as bob returns 403", r.status_code == 403, detail=f"got {r.status_code}")
    r = c.patch(f"/users/{ALICE}", json={"bio": "hijack"})
    check("PATCH /users/{alice} without token returns 401", r.status_code == 401, detail=f"got {r.status_code}")

    # DELETE is now author-only
    r = c.post("/posts", json={"message": "to be deleted"}, headers={"X-Username": ALICE, **alice_auth})
    pid = r.json()["id"]
    r = c.delete(f"/posts/{pid}", headers=bob_auth)
    check("DELETE /posts/{id} by non-author returns 403", r.status_code == 403, detail=f"got {r.status_code}")
    r = c.delete(f"/posts/{pid}")
    check("DELETE /posts/{id} without token returns 401", r.status_code == 401, detail=f"got {r.status_code}")
    r = c.delete(f"/posts/{pid}", headers=alice_auth)
    check("DELETE /posts/{id} by author cleans up returns 204", r.status_code == 204, detail=f"got {r.status_code}")

    # Logout revokes the token
    dispose_pw = "dispose_pw_12345"
    dispose_user = f"dispose_{RUN}"
    dispose_token = register_and_login(c, dispose_user, dispose_pw)
    r = c.post("/logout", headers=auth(dispose_token))
    check("POST /logout returns 204", r.status_code == 204, detail=f"got {r.status_code}")
    r = c.post(
        "/posts",
        json={"message": "after logout"},
        headers={"X-Username": dispose_user, **auth(dispose_token)},
    )
    check("POST /posts with revoked token returns 401", r.status_code == 401, detail=f"got {r.status_code}")


# ==========================================================================
# BOARD CHECKS (Gold, beyond the A2 spec)
# ==========================================================================

def run_board_checks(c: httpx.Client, state: dict) -> None:
    alice_auth = auth(state["alice_token"])

    # Post with no board falls into general.
    r = c.post(
        "/posts",
        json={"message": "defaults to general"},
        headers={"X-Username": ALICE, **alice_auth},
    )
    check("POST /posts without board returns 201", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        check("POST /posts without board goes to general", body.get("board") == "general", detail=str(body))

    # Post to a named board creates it and tags the post.
    board = f"tech_{RUN}"
    r = c.post(
        "/posts",
        json={"message": "into a new board", "board": board},
        headers={"X-Username": ALICE, **alice_auth},
    )
    check(f"POST /posts with board={board} returns 201", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        check(f"POST /posts response.board == {board}", r.json().get("board") == board)

    # Board is normalized to lowercase.
    mixed = f"Mixed_{RUN}"
    r = c.post(
        "/posts",
        json={"message": "case test", "board": mixed.lower()},
        headers={"X-Username": ALICE, **alice_auth},
    )
    # (we post only lowercase now — the lowercasing is documented for user-space
    # callers that might send e.g. "General")

    # Invalid board name (spaces) -> 422
    r = c.post(
        "/posts",
        json={"message": "bad", "board": "bad board"},
        headers={"X-Username": ALICE, **alice_auth},
    )
    check("POST /posts with invalid board returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # Over-long board name -> 422
    r = c.post(
        "/posts",
        json={"message": "bad", "board": "x" * 31},
        headers={"X-Username": ALICE, **alice_auth},
    )
    check("POST /posts with 31-char board returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # GET /boards returns a list including general and our new board
    r = c.get("/boards")
    check("GET /boards returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        names = {b["name"] for b in r.json()}
        check(
            "GET /boards includes general and newly-created board",
            "general" in names and board in names,
            detail=f"got {names}",
        )
        keys_ok = all(set(b.keys()) == BOARD_SHAPE for b in r.json())
        check("GET /boards items have exactly the board shape", keys_ok, detail="one or more had different keys")

    # GET /boards/{name} existing
    r = c.get(f"/boards/{board}")
    check(f"GET /boards/{board} returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        check(f"GET /boards/{board} has board shape", set(r.json().keys()) == BOARD_SHAPE, detail=str(r.json()))
        check(f"GET /boards/{board} post_count >= 1", r.json().get("post_count", 0) >= 1)

    # GET /boards/{unknown} -> 404
    r = c.get(f"/boards/nope_{RUN}")
    check("GET /boards/{unknown} returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # GET /boards/{name}/posts filters correctly
    r = c.get(f"/boards/{board}/posts")
    check(f"GET /boards/{board}/posts returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        posts = r.json()
        check(
            f"GET /boards/{board}/posts returns only that board",
            all(p.get("board") == board for p in posts) and len(posts) >= 1,
            detail=str(posts),
        )
        keys_ok = all(set(p.keys()) == POST_SHAPE for p in posts)
        check(f"GET /boards/{board}/posts items have gold post shape", keys_ok, detail="shape mismatch")

    # Unknown board on the posts sub-route -> 404
    r = c.get(f"/boards/unknown_{RUN}/posts")
    check("GET /boards/{unknown}/posts returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # ?board= filter on /posts composes with ?username= and ?q=
    r = c.get("/posts", params={"board": board, "username": ALICE})
    check("GET /posts?board=&username= returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        posts = r.json()
        check(
            "GET /posts?board=&username= returns only rows matching both",
            all(p.get("board") == board and p.get("username") == ALICE for p in posts) and len(posts) >= 1,
            detail=str(posts),
        )


if __name__ == "__main__":
    sys.exit(main())
