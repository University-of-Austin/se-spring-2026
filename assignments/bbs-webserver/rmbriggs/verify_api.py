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

import base64
import json
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
    # ==================================================================
    run_delete_checks(c, state)

    # ==================================================================
    # STUDENT TODO #2: pagination on GET /posts
    # ==================================================================
    run_pagination_checks(c, state)

    # ==================================================================
    # STUDENT TODO #3: exact response field shapes
    # ==================================================================
    run_field_shape_checks(c, state)

    # ==================================================================
    # Silver checks
    # ==================================================================
    run_bio_checks(c, state)
    run_patch_post_checks(c, state)
    run_username_filter_checks(c, state)

    # ==================================================================
    # Gold checks
    # ==================================================================
    run_board_checks(c, state)
    run_reaction_checks(c, state)
    run_cursor_pagination_checks(c, state)

    print()
    print(f"{PASSED} passed, {FAILED} failed")
    return 0 if FAILED == 0 else 1


# ── Bronze: shipped checks ────────────────────────────────────────

def run_user_checks(c: httpx.Client, state: dict) -> None:
    r = c.post("/users", json={"username": ALICE})
    check("POST /users creates a user (201)", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        check(
            "POST /users response has expected keys",
            "username" in body and "created_at" in body and body["username"] == ALICE,
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
            "POST /posts response has id, username, message, created_at",
            all(k in body for k in ("id", "username", "message", "created_at")),
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


# ── Bronze: student TODO implementations ──────────────────────────

def run_delete_checks(c: httpx.Client, state: dict) -> None:
    r = c.post("/posts", json={"message": "to be deleted"}, headers={"X-Username": ALICE})
    assert r.status_code == 201
    delete_id = r.json()["id"]

    r = c.delete(f"/posts/{delete_id}")
    check("DELETE /posts/{id} existing post returns 204", r.status_code == 204, detail=f"got {r.status_code}")

    r = c.get(f"/posts/{delete_id}")
    check("GET /posts/{id} after DELETE returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    r = c.delete("/posts/99999999")
    check("DELETE /posts/99999999 nonexistent returns 404", r.status_code == 404, detail=f"got {r.status_code}")


def run_pagination_checks(c: httpx.Client, state: dict) -> None:
    r = c.get("/posts", params={"limit": 2})
    check("GET /posts?limit=2 returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        check(
            "GET /posts?limit=2 returns at most 2 items",
            len(r.json()) <= 2,
            detail=f"got {len(r.json())} items",
        )

    all_posts = c.get("/posts", params={"limit": 200}).json()
    if len(all_posts) >= 2:
        r = c.get("/posts", params={"offset": 1, "limit": 200})
        check("GET /posts?offset=1 returns 200", r.status_code == 200, detail=f"got {r.status_code}")
        if r.status_code == 200:
            offset_posts = r.json()
            check(
                "GET /posts?offset=1 skips the first post",
                len(offset_posts) == len(all_posts) - 1,
                detail=f"expected {len(all_posts) - 1}, got {len(offset_posts)}",
            )

    r = c.get("/posts", params={"limit": 0})
    check("GET /posts?limit=0 returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.get("/posts", params={"limit": 500})
    check("GET /posts?limit=500 returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.get("/posts", params={"offset": -1})
    check("GET /posts?offset=-1 returns 422", r.status_code == 422, detail=f"got {r.status_code}")


def run_field_shape_checks(c: httpx.Client, state: dict) -> None:
    expected_user_keys = {"username", "created_at", "bio", "post_count"}
    expected_post_keys = {"id", "username", "message", "created_at", "updated_at", "board", "reaction_counts"}

    shape_user = f"shape_{RUN}"
    r = c.post("/users", json={"username": shape_user})
    if r.status_code == 201:
        body = r.json()
        check(
            "Field shape: POST /users keys",
            set(body.keys()) == expected_user_keys,
            detail=f"got {set(body.keys())}",
        )

    r = c.get(f"/users/{shape_user}")
    if r.status_code == 200:
        body = r.json()
        check(
            "Field shape: GET /users/{username} keys",
            set(body.keys()) == expected_user_keys,
            detail=f"got {set(body.keys())}",
        )

    r = c.get("/users")
    if r.status_code == 200:
        users = r.json()
        if users:
            check(
                "Field shape: GET /users items keys",
                all(set(u.keys()) == expected_user_keys for u in users),
                detail=f"first item keys: {set(users[0].keys())}",
            )

    r = c.post("/posts", json={"message": "shape test"}, headers={"X-Username": shape_user})
    shape_post_id = None
    if r.status_code == 201:
        body = r.json()
        shape_post_id = body.get("id")
        check(
            "Field shape: POST /posts keys",
            set(body.keys()) == expected_post_keys,
            detail=f"got {set(body.keys())}",
        )

    if shape_post_id:
        r = c.get(f"/posts/{shape_post_id}")
        if r.status_code == 200:
            body = r.json()
            check(
                "Field shape: GET /posts/{id} keys",
                set(body.keys()) == expected_post_keys,
                detail=f"got {set(body.keys())}",
            )

    r = c.get("/posts")
    if r.status_code == 200:
        posts = r.json()
        if posts:
            check(
                "Field shape: GET /posts items keys",
                all(set(p.keys()) == expected_post_keys for p in posts),
                detail=f"first item keys: {set(posts[0].keys())}",
            )


# ── Silver checks ─────────────────────────────────────────────────

def run_bio_checks(c: httpx.Client, state: dict) -> None:
    r = c.patch(f"/users/{ALICE}", json={"bio": "wolf in dog suit"})
    check("PATCH /users/{username} returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        body = r.json()
        check("PATCH /users bio updated", body.get("bio") == "wolf in dog suit", detail=f"got bio={body.get('bio')}")
        check("PATCH /users has post_count", "post_count" in body and isinstance(body["post_count"], int), detail=str(body))

    r = c.get(f"/users/{ALICE}")
    if r.status_code == 200:
        check("GET /users reflects updated bio", r.json().get("bio") == "wolf in dog suit")

    r = c.get(f"/users/{ALICE}")
    if r.status_code == 200:
        api_count = r.json().get("post_count", -1)
        alice_posts = c.get(f"/users/{ALICE}/posts").json()
        check("post_count matches actual posts", api_count == len(alice_posts),
              detail=f"post_count={api_count}, actual={len(alice_posts)}")

    fresh = f"fresh_{RUN}"
    r = c.post("/users", json={"username": fresh})
    if r.status_code == 201:
        body = r.json()
        check("New user bio=null", body.get("bio") is None)
        check("New user post_count=0", body.get("post_count") == 0)

    r = c.patch(f"/users/{GHOST}", json={"bio": "nope"})
    check("PATCH /users/{ghost} returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    r = c.patch(f"/users/{ALICE}", json={"bio": "x" * 201})
    check("PATCH /users bio > 200 returns 422", r.status_code == 422, detail=f"got {r.status_code}")


def run_patch_post_checks(c: httpx.Client, state: dict) -> None:
    r = c.post("/posts", json={"message": "original message"}, headers={"X-Username": ALICE})
    assert r.status_code == 201
    edit_id = r.json()["id"]

    r = c.patch(f"/posts/{edit_id}", json={"message": "edited message"}, headers={"X-Username": ALICE})
    check("PATCH /posts/{id} returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        body = r.json()
        check("PATCH /posts message updated", body.get("message") == "edited message")
        check("PATCH /posts sets updated_at", body.get("updated_at") is not None)

    r = c.get(f"/posts/{edit_id}")
    if r.status_code == 200:
        check("GET reflects edited message", r.json().get("message") == "edited message")

    r = c.patch(f"/posts/{edit_id}", json={"message": "hacked"}, headers={"X-Username": BOB})
    check("PATCH /posts by non-author returns 403", r.status_code == 403, detail=f"got {r.status_code}")

    r = c.get(f"/posts/{edit_id}")
    if r.status_code == 200:
        check("Message unchanged after 403", r.json().get("message") == "edited message")

    r = c.patch("/posts/99999999", json={"message": "nope"}, headers={"X-Username": ALICE})
    check("PATCH /posts/99999999 returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    r = c.patch(f"/posts/{edit_id}", json={"message": "no header"})
    check("PATCH /posts without X-Username returns 400", r.status_code == 400, detail=f"got {r.status_code}")

    r = c.patch(f"/posts/{edit_id}", json={"message": ""}, headers={"X-Username": ALICE})
    check("PATCH /posts empty message returns 422", r.status_code == 422, detail=f"got {r.status_code}")


def run_username_filter_checks(c: httpx.Client, state: dict) -> None:
    r = c.get("/posts", params={"username": ALICE})
    check(f"GET /posts?username={ALICE} returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        posts = r.json()
        check(
            "username filter: only alice's posts",
            all(p.get("username") == ALICE for p in posts) and len(posts) >= 1,
            detail=f"got {len(posts)} posts",
        )

    needle = f"needle_{RUN}"
    r = c.get("/posts", params={"username": ALICE, "q": needle})
    check("GET /posts?username=...&q=... returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        posts = r.json()
        check(
            "username + q filter works",
            all(p.get("username") == ALICE and needle in p.get("message", "") for p in posts) and len(posts) >= 1,
        )

    r = c.get("/posts", params={"username": ALICE, "limit": 1})
    check(
        "username + limit composable",
        r.status_code == 200 and len(r.json()) <= 1,
    )

    r = c.get("/posts", params={"username": GHOST})
    check(
        "GET /posts?username=ghost returns empty array",
        r.status_code == 200 and r.json() == [],
    )


# ── Gold checks ───────────────────────────────────────────────────

def run_board_checks(c: httpx.Client, state: dict) -> None:
    board_name = f"general_{RUN}"

    # Create a board
    r = c.post("/boards", json={"name": board_name, "description": "General discussion"})
    check("POST /boards returns 201", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        check("POST /boards has name", body.get("name") == board_name)
        check("POST /boards has description", body.get("description") == "General discussion")
        check("POST /boards has created_at", "created_at" in body)
        check("POST /boards has post_count=0", body.get("post_count") == 0)

    # Duplicate board returns 409
    r = c.post("/boards", json={"name": board_name})
    check("POST /boards duplicate returns 409", r.status_code == 409, detail=f"got {r.status_code}")

    # List boards
    r = c.get("/boards")
    check("GET /boards returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        names = [b["name"] for b in r.json()]
        check("GET /boards includes created board", board_name in names)

    # Get single board
    r = c.get(f"/boards/{board_name}")
    check(f"GET /boards/{board_name} returns 200", r.status_code == 200, detail=f"got {r.status_code}")

    # Get nonexistent board
    r = c.get(f"/boards/nonexistent_{RUN}")
    check("GET /boards/nonexistent returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # Post to a board
    r = c.post("/posts", json={"message": "board post", "board": board_name}, headers={"X-Username": ALICE})
    check("POST /posts with board returns 201", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        check("POST /posts response has board field", body.get("board") == board_name, detail=f"got board={body.get('board')}")
        state["board_post_id"] = body.get("id")

    # Post without board has board=null
    r = c.post("/posts", json={"message": "no board post"}, headers={"X-Username": ALICE})
    if r.status_code == 201:
        check("POST /posts without board has board=null", r.json().get("board") is None)

    # Post to nonexistent board returns 404
    r = c.post("/posts", json={"message": "bad board", "board": f"fake_{RUN}"}, headers={"X-Username": ALICE})
    check("POST /posts with nonexistent board returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # Get board posts
    r = c.get(f"/boards/{board_name}/posts")
    check(f"GET /boards/{board_name}/posts returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        posts = r.json()
        check(
            "Board posts contain only board posts",
            all(p.get("board") == board_name for p in posts) and len(posts) >= 1,
            detail=f"got {len(posts)} posts",
        )

    # Get board posts for nonexistent board
    r = c.get(f"/boards/nonexistent_{RUN}/posts")
    check("GET /boards/nonexistent/posts returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # Board post_count reflects actual count
    r = c.get(f"/boards/{board_name}")
    if r.status_code == 200:
        check("Board post_count >= 1 after posting", r.json().get("post_count", 0) >= 1)

    # Filter GET /posts by board
    r = c.get("/posts", params={"board": board_name})
    check("GET /posts?board=... returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        posts = r.json()
        check(
            "GET /posts?board filter works",
            all(p.get("board") == board_name for p in posts) and len(posts) >= 1,
        )


def run_reaction_checks(c: httpx.Client, state: dict) -> None:
    # Create a post for reaction tests
    r = c.post("/posts", json={"message": "react to me"}, headers={"X-Username": ALICE})
    assert r.status_code == 201
    react_post_id = r.json()["id"]

    # Add a reaction
    r = c.post(f"/posts/{react_post_id}/reactions", json={"kind": "+1"}, headers={"X-Username": ALICE})
    check("POST /posts/{id}/reactions returns 201", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        check("Reaction has post_id", body.get("post_id") == react_post_id)
        check("Reaction has username", body.get("username") == ALICE)
        check("Reaction has kind", body.get("kind") == "+1")

    # Duplicate reaction returns 409
    r = c.post(f"/posts/{react_post_id}/reactions", json={"kind": "+1"}, headers={"X-Username": ALICE})
    check("Duplicate reaction returns 409", r.status_code == 409, detail=f"got {r.status_code}")

    # Different kind from same user is OK
    r = c.post(f"/posts/{react_post_id}/reactions", json={"kind": "heart"}, headers={"X-Username": ALICE})
    check("Different kind from same user returns 201", r.status_code == 201, detail=f"got {r.status_code}")

    # Different user same kind is OK
    r = c.post(f"/posts/{react_post_id}/reactions", json={"kind": "+1"}, headers={"X-Username": BOB})
    check("Same kind from different user returns 201", r.status_code == 201, detail=f"got {r.status_code}")

    # Invalid reaction kind returns 422
    r = c.post(f"/posts/{react_post_id}/reactions", json={"kind": "invalid"}, headers={"X-Username": ALICE})
    check("Invalid reaction kind returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # Reaction on nonexistent post returns 404
    r = c.post("/posts/99999999/reactions", json={"kind": "+1"}, headers={"X-Username": ALICE})
    check("Reaction on nonexistent post returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # Missing X-Username returns 400
    r = c.post(f"/posts/{react_post_id}/reactions", json={"kind": "+1"})
    check("Reaction without X-Username returns 400", r.status_code == 400, detail=f"got {r.status_code}")

    # List reactions
    r = c.get(f"/posts/{react_post_id}/reactions")
    check("GET /posts/{id}/reactions returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        reactions = r.json()
        check("GET reactions returns a list", isinstance(reactions, list) and len(reactions) >= 3,
              detail=f"got {len(reactions)} reactions")

    # List reactions on nonexistent post
    r = c.get("/posts/99999999/reactions")
    check("GET reactions on nonexistent post returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # Verify reaction_counts in post response
    r = c.get(f"/posts/{react_post_id}")
    if r.status_code == 200:
        body = r.json()
        rc = body.get("reaction_counts", {})
        check("Post has reaction_counts", isinstance(rc, dict), detail=str(rc))
        check("reaction_counts['+1'] == 2", rc.get("+1") == 2, detail=f"got {rc.get('+1')}")
        check("reaction_counts['heart'] == 1", rc.get("heart") == 1, detail=f"got {rc.get('heart')}")

    # Delete reactions by user
    r = c.delete(f"/posts/{react_post_id}/reactions/{BOB}")
    check("DELETE /posts/{id}/reactions/{username} returns 204", r.status_code == 204, detail=f"got {r.status_code}")

    # Verify reaction was removed
    r = c.get(f"/posts/{react_post_id}")
    if r.status_code == 200:
        rc = r.json().get("reaction_counts", {})
        check("After delete, +1 count decremented", rc.get("+1") == 1, detail=f"got {rc.get('+1')}")

    # Delete nonexistent reaction
    r = c.delete(f"/posts/{react_post_id}/reactions/{GHOST}")
    check("DELETE nonexistent reaction returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # Delete reaction on nonexistent post
    r = c.delete(f"/posts/99999999/reactions/{ALICE}")
    check("DELETE reaction on nonexistent post returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # Reactions are removed when post is deleted
    r = c.post("/posts", json={"message": "delete me with reactions"}, headers={"X-Username": ALICE})
    assert r.status_code == 201
    tmp_id = r.json()["id"]
    c.post(f"/posts/{tmp_id}/reactions", json={"kind": "fire"}, headers={"X-Username": ALICE})
    r = c.delete(f"/posts/{tmp_id}")
    check("DELETE post with reactions returns 204", r.status_code == 204, detail=f"got {r.status_code}")
    r = c.get(f"/posts/{tmp_id}/reactions")
    check("Reactions gone after post delete (404)", r.status_code == 404, detail=f"got {r.status_code}")


def run_cursor_pagination_checks(c: httpx.Client, state: dict) -> None:
    # Create enough posts for pagination testing
    cursor_user = f"cursor_{RUN}"
    c.post("/users", json={"username": cursor_user})
    for i in range(5):
        c.post("/posts", json={"message": f"cursor_test_{RUN}_{i}"}, headers={"X-Username": cursor_user})

    # First page with cursor (pass empty-ish cursor to trigger envelope)
    r = c.get("/posts", params={"cursor": "", "limit": 2})
    check("GET /posts?cursor=&limit=2 returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        body = r.json()
        check("Cursor response is envelope", "posts" in body and "next_cursor" in body and "has_more" in body,
              detail=str(list(body.keys())))
        check("Cursor page has <= 2 posts", len(body.get("posts", [])) <= 2)
        check("has_more is true", body.get("has_more") is True)

        # Second page using next_cursor
        next_cursor = body.get("next_cursor")
        if next_cursor:
            r2 = c.get("/posts", params={"cursor": next_cursor, "limit": 2})
            check("Second cursor page returns 200", r2.status_code == 200, detail=f"got {r2.status_code}")
            if r2.status_code == 200:
                body2 = r2.json()
                check("Second page is envelope", "posts" in body2)
                page1_ids = {p["id"] for p in body["posts"]}
                page2_ids = {p["id"] for p in body2["posts"]}
                check("No duplicate posts across pages", len(page1_ids & page2_ids) == 0,
                      detail=f"overlap: {page1_ids & page2_ids}")
                check("Page 2 ids > page 1 ids", min(page2_ids) > max(page1_ids) if page2_ids else True)

    # Without cursor, returns bare array (backwards compat)
    r = c.get("/posts", params={"limit": 2})
    check("GET /posts without cursor returns bare array", r.status_code == 200 and isinstance(r.json(), list),
          detail=f"type={type(r.json()).__name__}")

    # Page through all posts, collect all IDs, verify no duplicates
    all_ids = []
    cur = ""
    pages = 0
    while pages < 50:  # safety limit
        r = c.get("/posts", params={"cursor": cur, "limit": 3})
        if r.status_code != 200:
            break
        body = r.json()
        posts = body.get("posts", [])
        all_ids.extend(p["id"] for p in posts)
        if not body.get("has_more") or not body.get("next_cursor"):
            break
        cur = body["next_cursor"]
        pages += 1

    check("Full cursor walk: no duplicate IDs", len(all_ids) == len(set(all_ids)),
          detail=f"total={len(all_ids)}, unique={len(set(all_ids))}")
    check("Full cursor walk: IDs are ascending", all_ids == sorted(all_ids),
          detail=f"first few: {all_ids[:5]}")

    # Verify cursor is base64 encoded JSON
    if next_cursor:
        try:
            decoded = json.loads(base64.b64decode(next_cursor))
            check("Cursor is base64-encoded JSON with 'id'", "id" in decoded, detail=str(decoded))
        except Exception as e:
            check("Cursor is base64-encoded JSON", False, detail=str(e))


if __name__ == "__main__":
    sys.exit(main())
