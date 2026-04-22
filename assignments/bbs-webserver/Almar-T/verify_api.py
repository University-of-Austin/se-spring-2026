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

====================================================================
CHANGES FROM THE SHIPPED STARTER (Almar-T, gold tier)
====================================================================

Two shipped assertions — the shape checks on POST /users (originally
line 131-135) and POST /posts (originally line 180-185) — asserted
the BRONZE response shapes:

    POST /users response == {username, created_at}
    POST /posts response == {id, username, message, created_at}

The silver tier mandates adding `bio` and `post_count` to every user
response, and `updated_at` to every post response. The gold tier
adds `board` to every post response. Running those shipped checks
unchanged at gold would fail against a spec-conformant API, because
the API correctly includes the silver/gold fields.

Both checks are updated below to expect the gold shape:

    POST /users  ->  {username, created_at, bio, post_count}
    POST /posts  ->  {id, username, message, created_at, updated_at, board}

The check names are prefixed "(gold shape)" so it's obvious in the
test output that the expectation changed.

STUDENT TODO #1, #2, #3 are implemented below. The calls are
uncommented in main(). Additional silver and gold assertions
(PATCH, filter, reactions, boards) live in their own functions.
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

# Expected response shapes at the targeted tier (gold).
USER_SHAPE = {"username", "created_at", "bio", "post_count"}
POST_SHAPE = {"id", "username", "message", "created_at", "updated_at", "board"}
REACTION_SHAPE = {"post_id", "username", "kind"}
BOARD_SHAPE = {"name", "description", "created_at"}

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

    # Silver + gold extensions
    run_silver_user_checks(c, state)
    run_silver_post_checks(c, state)
    run_silver_filter_checks(c, state)
    run_gold_reaction_checks(c, state)
    run_gold_board_checks(c, state)

    print()
    print(f"{PASSED} passed, {FAILED} failed")
    return 0 if FAILED == 0 else 1


# ===========================================================================
# Shipped checks (two shape assertions updated for gold — see header note)
# ===========================================================================

def run_user_checks(c: httpx.Client, state: dict) -> None:
    r = c.post("/users", json={"username": ALICE})
    check("POST /users creates a user (201)", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        check(
            "POST /users response has exactly {username, created_at, bio, post_count} (gold shape)",
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
            "POST /posts response has exactly "
            "{id, username, message, created_at, updated_at, board} (gold shape)",
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


# ===========================================================================
# STUDENT TODO #1 — DELETE /posts/{id}
# ===========================================================================

def run_delete_checks(c: httpx.Client, state: dict) -> None:
    # Create a fresh post specifically to delete, so we don't stomp on
    # state["alice_post_id"] that later checks may still rely on.
    r = c.post("/posts", json={"message": "to be deleted"}, headers={"X-Username": ALICE})
    if r.status_code != 201:
        check("DELETE setup: create victim post", False, detail=f"got {r.status_code}")
        return
    victim_id = r.json()["id"]

    r = c.delete(f"/posts/{victim_id}")
    check(f"DELETE /posts/{victim_id} returns 204", r.status_code == 204, detail=f"got {r.status_code}")
    check(f"DELETE /posts/{victim_id} has empty body", r.content == b"", detail=f"got {r.content!r}")

    r = c.get(f"/posts/{victim_id}")
    check(
        f"GET /posts/{victim_id} after DELETE returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    r = c.delete("/posts/99999999")
    check(
        "DELETE /posts/99999999 (nonexistent) returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )


# ===========================================================================
# STUDENT TODO #2 — pagination on GET /posts
# ===========================================================================

def run_pagination_checks(c: httpx.Client, state: dict) -> None:
    # Ensure at least ~5 posts exist so limit/offset has material to bite on.
    for i in range(5):
        c.post(
            "/posts",
            json={"message": f"pagination setup {RUN}-{i}"},
            headers={"X-Username": ALICE},
        )

    r = c.get("/posts", params={"limit": 3})
    check("GET /posts?limit=3 returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        items = r.json()
        check(
            "GET /posts?limit=3 returns at most 3 items",
            len(items) <= 3,
            detail=f"got {len(items)}",
        )

    # Consistency: offset=K should skip exactly the first K items (assuming
    # no inserts between calls — we're the only client). Use a smaller limit
    # on the offset request so base[2:2+N] and offs align in length.
    base = c.get("/posts", params={"limit": 10}).json()
    if len(base) >= 5:
        offs = c.get("/posts", params={"limit": 3, "offset": 2}).json()
        check(
            "GET /posts?offset=2 skips the first 2 items",
            offs == base[2:5],
            detail=f"base[:5]={[p['id'] for p in base[:5]]} offs={[p['id'] for p in offs]}",
        )

    r = c.get("/posts", params={"limit": 0})
    check("GET /posts?limit=0 returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.get("/posts", params={"limit": 500})
    check("GET /posts?limit=500 returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.get("/posts", params={"offset": -1})
    check("GET /posts?offset=-1 returns 422", r.status_code == 422, detail=f"got {r.status_code}")


# ===========================================================================
# STUDENT TODO #3 — exact response field shapes
#
# Asserts `set(body.keys()) == EXPECTED_SHAPE` on every endpoint that
# returns a user or a post. Stray fields fail, missing fields fail.
# Shapes reflect the silver+gold additions (bio, post_count, updated_at,
# board).
# ===========================================================================

def run_field_shape_checks(c: httpx.Client, state: dict) -> None:
    # Fresh isolated fixtures so this function doesn't depend on state
    # left over by earlier runs.
    uname = f"shape_{RUN}"
    c.post("/users", json={"username": uname})

    # -- user shape on POST /users --
    r = c.post("/users", json={"username": uname + "_b"})
    check(
        "shape: POST /users -> exactly user fields",
        r.status_code == 201 and set(r.json().keys()) == USER_SHAPE,
        detail=str(r.json()) if r.status_code == 201 else f"status {r.status_code}",
    )

    # -- user shape on GET /users/{username} --
    r = c.get(f"/users/{uname}")
    check(
        "shape: GET /users/{u} -> exactly user fields",
        r.status_code == 200 and set(r.json().keys()) == USER_SHAPE,
        detail=str(r.json()) if r.status_code == 200 else f"status {r.status_code}",
    )

    # -- user shape on items in GET /users --
    r = c.get("/users")
    if r.status_code == 200 and r.json():
        item = r.json()[0]
        check(
            "shape: items in GET /users -> exactly user fields",
            set(item.keys()) == USER_SHAPE,
            detail=str(item),
        )

    # -- post shape on POST /posts --
    r = c.post("/posts", json={"message": "shape check"}, headers={"X-Username": uname})
    shape_post_id = r.json().get("id") if r.status_code == 201 else None
    check(
        "shape: POST /posts -> exactly post fields",
        r.status_code == 201 and set(r.json().keys()) == POST_SHAPE,
        detail=str(r.json()) if r.status_code == 201 else f"status {r.status_code}",
    )

    # -- post shape on GET /posts/{id} --
    if shape_post_id:
        r = c.get(f"/posts/{shape_post_id}")
        check(
            "shape: GET /posts/{id} -> exactly post fields",
            r.status_code == 200 and set(r.json().keys()) == POST_SHAPE,
            detail=str(r.json()) if r.status_code == 200 else f"status {r.status_code}",
        )

    # -- post shape on items in GET /posts --
    r = c.get("/posts", params={"limit": 1})
    if r.status_code == 200 and r.json():
        check(
            "shape: items in GET /posts -> exactly post fields",
            set(r.json()[0].keys()) == POST_SHAPE,
            detail=str(r.json()[0]),
        )


# ===========================================================================
# Silver additions — PATCH endpoints, ?username= filter, bio & post_count
# ===========================================================================

def run_silver_user_checks(c: httpx.Client, state: dict) -> None:
    uname = f"silveruser_{RUN}"
    c.post("/users", json={"username": uname})

    # Before PATCH: bio is empty, post_count starts at 0
    body = c.get(f"/users/{uname}").json()
    check("silver: new user has empty bio", body.get("bio") == "", detail=str(body))
    check("silver: new user has post_count == 0", body.get("post_count") == 0, detail=str(body))

    # PATCH bio
    r = c.patch(f"/users/{uname}", json={"bio": "wolf in dog suit"})
    check("PATCH /users/{u} returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        check(
            "PATCH /users/{u} response bio matches",
            r.json().get("bio") == "wolf in dog suit",
            detail=str(r.json()),
        )

    # PATCH bio too long -> 422
    r = c.patch(f"/users/{uname}", json={"bio": "x" * 201})
    check("PATCH /users/{u} bio over 200 chars returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # PATCH unknown user -> 404
    r = c.patch(f"/users/{GHOST}", json={"bio": "nope"})
    check("PATCH /users/{ghost} returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # post_count tracks posts
    c.post("/posts", json={"message": "p1"}, headers={"X-Username": uname})
    c.post("/posts", json={"message": "p2"}, headers={"X-Username": uname})
    body = c.get(f"/users/{uname}").json()
    check("silver: post_count reflects posts made", body.get("post_count") >= 2, detail=str(body))


def run_silver_post_checks(c: httpx.Client, state: dict) -> None:
    # Author-only PATCH policy: only the original author can edit.
    author = f"silverauth_{RUN}"
    intruder = f"silverint_{RUN}"
    c.post("/users", json={"username": author})
    c.post("/users", json={"username": intruder})

    r = c.post("/posts", json={"message": "original text"}, headers={"X-Username": author})
    pid = r.json()["id"]

    # Author can edit
    r = c.patch(f"/posts/{pid}", json={"message": "edited by author"}, headers={"X-Username": author})
    check("PATCH /posts/{id} by author returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        body = r.json()
        check(
            "PATCH /posts/{id} response has updated_at populated",
            body.get("updated_at") is not None,
            detail=str(body),
        )
        check(
            "PATCH /posts/{id} message was updated",
            body.get("message") == "edited by author",
            detail=str(body),
        )
        check(
            "PATCH /posts/{id} response has exactly post fields",
            set(body.keys()) == POST_SHAPE,
            detail=str(body),
        )

    # Intruder cannot edit
    r = c.patch(
        f"/posts/{pid}",
        json={"message": "hacked"},
        headers={"X-Username": intruder},
    )
    check(
        "PATCH /posts/{id} by non-author returns 403",
        r.status_code == 403,
        detail=f"got {r.status_code}",
    )

    # Missing X-Username -> 400
    r = c.patch(f"/posts/{pid}", json={"message": "anon"})
    check(
        "PATCH /posts/{id} without X-Username returns 400",
        r.status_code == 400,
        detail=f"got {r.status_code}",
    )

    # Empty message -> 422
    r = c.patch(f"/posts/{pid}", json={"message": ""}, headers={"X-Username": author})
    check(
        "PATCH /posts/{id} empty message returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # Nonexistent post -> 404
    r = c.patch("/posts/99999999", json={"message": "x"}, headers={"X-Username": author})
    check(
        "PATCH /posts/99999999 returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )


def run_silver_filter_checks(c: httpx.Client, state: dict) -> None:
    # ?username= filter, composable with ?q= and pagination.
    u = f"silverfilt_{RUN}"
    c.post("/users", json={"username": u})
    marker = f"marker{RUN}"
    c.post("/posts", json={"message": f"{marker} one"}, headers={"X-Username": u})
    c.post("/posts", json={"message": f"{marker} two"}, headers={"X-Username": u})
    c.post("/posts", json={"message": "unrelated"}, headers={"X-Username": u})

    r = c.get("/posts", params={"username": u})
    check(f"GET /posts?username={u} returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        items = r.json()
        check(
            f"GET /posts?username={u} returns only that user's posts",
            all(p["username"] == u for p in items) and len(items) >= 3,
            detail=str(items[:3]),
        )

    # Composability: ?username= AND ?q=
    r = c.get("/posts", params={"username": u, "q": marker})
    if r.status_code == 200:
        items = r.json()
        check(
            "GET /posts?username&q composes",
            all(p["username"] == u and marker in p["message"] for p in items) and len(items) >= 2,
            detail=str(items),
        )

    # Composability: ?username= AND ?limit=
    r = c.get("/posts", params={"username": u, "limit": 1})
    if r.status_code == 200:
        check(
            "GET /posts?username&limit composes",
            len(r.json()) <= 1,
            detail=str(r.json()),
        )


# ===========================================================================
# Gold additions — reactions + boards
# ===========================================================================

def run_gold_reaction_checks(c: httpx.Client, state: dict) -> None:
    author = f"goldreact_{RUN}"
    reactor = f"goldreact2_{RUN}"
    c.post("/users", json={"username": author})
    c.post("/users", json={"username": reactor})
    pid = c.post("/posts", json={"message": "react to me"}, headers={"X-Username": author}).json()["id"]

    # Create reaction
    r = c.post(f"/posts/{pid}/reactions", json={"username": reactor, "kind": "+1"})
    check("POST /posts/{id}/reactions returns 201", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        check(
            "POST /posts/{id}/reactions response has {post_id, username, kind}",
            set(body.keys()) == REACTION_SHAPE,
            detail=str(body),
        )
        check(
            "POST /posts/{id}/reactions response values correct",
            body["post_id"] == pid and body["username"] == reactor and body["kind"] == "+1",
            detail=str(body),
        )

    # Duplicate reaction -> 409
    r = c.post(f"/posts/{pid}/reactions", json={"username": reactor, "kind": "+1"})
    check("POST duplicate reaction returns 409", r.status_code == 409, detail=f"got {r.status_code}")

    # Unknown user -> 404
    r = c.post(f"/posts/{pid}/reactions", json={"username": GHOST, "kind": "+1"})
    check("POST reaction unknown user returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # Unknown post -> 404
    r = c.post("/posts/99999999/reactions", json={"username": reactor, "kind": "+1"})
    check("POST reaction unknown post returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # Delete reaction
    r = c.delete(f"/posts/{pid}/reactions/{reactor}")
    check("DELETE /posts/{id}/reactions/{u} returns 204", r.status_code == 204, detail=f"got {r.status_code}")

    # Delete again (none left) -> 404
    r = c.delete(f"/posts/{pid}/reactions/{reactor}")
    check(
        "DELETE /posts/{id}/reactions/{u} again returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    # Delete reaction on nonexistent post -> 404
    r = c.delete(f"/posts/99999999/reactions/{reactor}")
    check("DELETE reactions on unknown post returns 404", r.status_code == 404, detail=f"got {r.status_code}")


def run_gold_board_checks(c: httpx.Client, state: dict) -> None:
    # 'general' board is seeded in migration 003 and should always be present.
    r = c.get("/boards")
    check("GET /boards returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        boards = r.json()
        check(
            "GET /boards includes seeded 'general' board",
            any(b["name"] == "general" for b in boards),
            detail=str(boards),
        )
        if boards:
            check(
                "shape: items in GET /boards -> exactly {name, description, created_at}",
                set(boards[0].keys()) == BOARD_SHAPE,
                detail=str(boards[0]),
            )

    # Create a new board
    bname = f"b_{RUN}"
    r = c.post("/boards", json={"name": bname, "description": "test board"})
    check("POST /boards returns 201", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        check(
            "POST /boards response has exactly {name, description, created_at}",
            set(r.json().keys()) == BOARD_SHAPE,
            detail=str(r.json()),
        )

    # Duplicate board -> 409
    r = c.post("/boards", json={"name": bname})
    check("POST /boards duplicate returns 409", r.status_code == 409, detail=f"got {r.status_code}")

    # Invalid board name (has space) -> 422
    r = c.post("/boards", json={"name": "has space"})
    check("POST /boards invalid name returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # Create a post in the new board
    author = f"goldboard_{RUN}"
    c.post("/users", json={"username": author})
    r = c.post(
        "/posts",
        json={"message": "in my board", "board": bname},
        headers={"X-Username": author},
    )
    check(f"POST /posts with board={bname} returns 201", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        check(
            "POST /posts response reflects board",
            r.json().get("board") == bname,
            detail=str(r.json()),
        )

    # Post to unknown board -> 404
    r = c.post(
        "/posts",
        json={"message": "nope", "board": f"nonexistent_{RUN}"},
        headers={"X-Username": author},
    )
    check("POST /posts with unknown board returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # GET /boards/{name}/posts returns only posts in that board
    r = c.get(f"/boards/{bname}/posts")
    check(f"GET /boards/{bname}/posts returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        items = r.json()
        check(
            f"GET /boards/{bname}/posts contains only posts in that board",
            all(p["board"] == bname for p in items) and len(items) >= 1,
            detail=str(items),
        )

    # Unknown board posts -> 404
    r = c.get(f"/boards/nonexistent_{RUN}/posts")
    check("GET /boards/{missing}/posts returns 404", r.status_code == 404, detail=f"got {r.status_code}")


if __name__ == "__main__":
    sys.exit(main())
