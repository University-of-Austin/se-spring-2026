"""
verify_api.py - conformance check for your BBS API.

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

Extended with silver and gold tier assertions.
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

    # STUDENT TODO #1 — DELETE /posts/{id}
    run_delete_checks(c, state)

    # STUDENT TODO #2 — pagination on GET /posts
    run_pagination_checks(c, state)

    # STUDENT TODO #3 — field shape checks
    run_field_shape_checks(c, state)

    # Silver tier checks
    run_silver_checks(c, state)

    # Gold tier checks
    run_gold_checks(c, state)

    print()
    print(f"{PASSED} passed, {FAILED} failed")
    return 0 if FAILED == 0 else 1


def run_user_checks(c: httpx.Client, state: dict) -> None:
    r = c.post("/users", json={"username": ALICE})
    check("POST /users creates a user (201)", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        # Silver tier: user responses include bio and post_count
        check(
            "POST /users response has exactly the expected fields",
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
        # Silver tier: post responses include updated_at
        expected_keys = {"id", "username", "message", "created_at", "updated_at"}
        check(
            "POST /posts response has exactly the expected fields",
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


# ======================================================================
# STUDENT TODO #1: DELETE /posts/{id}
# ======================================================================

def run_delete_checks(c: httpx.Client, state: dict) -> None:
    """Verify DELETE /posts/{id} behavior."""
    # Create a dedicated post to delete
    r = c.post("/posts", json={"message": "delete me"}, headers={"X-Username": ALICE})
    assert r.status_code == 201, f"Setup failed: could not create post to delete (got {r.status_code})"
    delete_id = r.json()["id"]

    # DELETE on an existing post returns 204
    r = c.delete(f"/posts/{delete_id}")
    check("DELETE /posts/{id} on existing post returns 204", r.status_code == 204, detail=f"got {r.status_code}")

    # After DELETE, GET on the same id returns 404
    r = c.get(f"/posts/{delete_id}")
    check("GET /posts/{id} after DELETE returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # DELETE on a post id that does not exist returns 404
    r = c.delete("/posts/99999999")
    check("DELETE /posts/99999999 (nonexistent) returns 404", r.status_code == 404, detail=f"got {r.status_code}")


# ======================================================================
# STUDENT TODO #2: pagination on GET /posts
# ======================================================================

def run_pagination_checks(c: httpx.Client, state: dict) -> None:
    """Verify limit/offset pagination on GET /posts."""
    # Ensure there are enough posts — create a few more
    for i in range(3):
        c.post("/posts", json={"message": f"pagination test {RUN} {i}"}, headers={"X-Username": ALICE})

    # GET /posts?limit=N returns at most N items
    r = c.get("/posts", params={"limit": 2})
    check("GET /posts?limit=2 returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        posts = r.json()
        check("GET /posts?limit=2 returns at most 2 items", len(posts) <= 2, detail=f"got {len(posts)}")

    # GET /posts?offset=K skips the first K items
    r_all = c.get("/posts", params={"limit": 200})
    r_offset = c.get("/posts", params={"limit": 200, "offset": 2})
    if r_all.status_code == 200 and r_offset.status_code == 200:
        all_posts = r_all.json()
        offset_posts = r_offset.json()
        check(
            "GET /posts?offset=2 skips the first 2 items",
            len(offset_posts) == max(0, len(all_posts) - 2),
            detail=f"all={len(all_posts)}, offset_2={len(offset_posts)}",
        )

    # GET /posts?limit=0 returns 422
    r = c.get("/posts", params={"limit": 0})
    check("GET /posts?limit=0 returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # GET /posts?limit=500 returns 422 (above max of 200)
    r = c.get("/posts", params={"limit": 500})
    check("GET /posts?limit=500 returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # GET /posts?offset=-1 returns 422
    r = c.get("/posts", params={"offset": -1})
    check("GET /posts?offset=-1 returns 422", r.status_code == 422, detail=f"got {r.status_code}")


# ======================================================================
# STUDENT TODO #3: field shape checks
# ======================================================================

def run_field_shape_checks(c: httpx.Client, state: dict) -> None:
    """Verify response bodies have exactly the expected fields.

    Bronze fields:
      - User: {username, created_at}
      - Post: {id, username, message, created_at}

    Since we implement silver, user responses also include bio and post_count,
    and post responses also include updated_at. We check for the silver shape.
    """
    # Expected field sets (silver tier)
    user_fields = {"username", "created_at", "bio", "post_count"}
    post_fields = {"id", "username", "message", "created_at", "updated_at"}

    # Check POST /users response shape
    test_user = f"shape_{RUN}"
    r = c.post("/users", json={"username": test_user})
    if r.status_code == 201:
        body = r.json()
        check(
            "POST /users response has exactly the expected fields",
            set(body.keys()) == user_fields,
            detail=f"expected {user_fields}, got {set(body.keys())}",
        )

    # Check GET /users/{username} response shape
    r = c.get(f"/users/{ALICE}")
    if r.status_code == 200:
        body = r.json()
        check(
            "GET /users/{username} response has exactly the expected fields",
            set(body.keys()) == user_fields,
            detail=f"expected {user_fields}, got {set(body.keys())}",
        )

    # Check GET /users list item shape
    r = c.get("/users")
    if r.status_code == 200:
        users = r.json()
        if users:
            check(
                "GET /users list item has exactly the expected fields",
                set(users[0].keys()) == user_fields,
                detail=f"expected {user_fields}, got {set(users[0].keys())}",
            )

    # Check POST /posts response shape
    r = c.post("/posts", json={"message": "shape check"}, headers={"X-Username": ALICE})
    if r.status_code == 201:
        body = r.json()
        check(
            "POST /posts response has exactly the expected fields",
            set(body.keys()) == post_fields,
            detail=f"expected {post_fields}, got {set(body.keys())}",
        )
        state["shape_post_id"] = body.get("id")

    # Check GET /posts/{id} response shape
    if "shape_post_id" in state:
        r = c.get(f"/posts/{state['shape_post_id']}")
        if r.status_code == 200:
            body = r.json()
            check(
                "GET /posts/{id} response has exactly the expected fields",
                set(body.keys()) == post_fields,
                detail=f"expected {post_fields}, got {set(body.keys())}",
            )

    # Check GET /posts list item shape
    r = c.get("/posts", params={"limit": 1})
    if r.status_code == 200:
        posts = r.json()
        if posts:
            check(
                "GET /posts list item has exactly the expected fields",
                set(posts[0].keys()) == post_fields,
                detail=f"expected {post_fields}, got {set(posts[0].keys())}",
            )

    # Clean up
    if "shape_post_id" in state:
        c.delete(f"/posts/{state['shape_post_id']}")


# ======================================================================
# SILVER TIER CHECKS
# ======================================================================

def run_silver_checks(c: httpx.Client, state: dict) -> None:
    """Verify silver-tier features: bio, post_count, PATCH, ?username= filter."""
    print()
    print("--- Silver tier ---")

    # --- bio and post_count in user responses ---
    r = c.get(f"/users/{ALICE}")
    if r.status_code == 200:
        body = r.json()
        check("GET /users/{username} includes bio field", "bio" in body, detail=str(body.keys()))
        check("GET /users/{username} includes post_count field", "post_count" in body, detail=str(body.keys()))
        check(
            "GET /users/{username} post_count is an integer >= 0",
            isinstance(body.get("post_count"), int) and body["post_count"] >= 0,
            detail=f"post_count={body.get('post_count')}",
        )

    # --- PATCH /users/{username} — update bio ---
    r = c.patch(f"/users/{ALICE}", json={"bio": "I am Alice"})
    check("PATCH /users/{username} returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        body = r.json()
        check("PATCH /users/{username} response bio is updated", body.get("bio") == "I am Alice", detail=str(body))

    # Verify bio persists
    r = c.get(f"/users/{ALICE}")
    if r.status_code == 200:
        check("GET /users/{username} bio persisted after PATCH", r.json().get("bio") == "I am Alice")

    # PATCH nonexistent user returns 404
    r = c.patch(f"/users/{GHOST}", json={"bio": "nope"})
    check("PATCH /users/{ghost} returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # PATCH with bio too long returns 422
    r = c.patch(f"/users/{ALICE}", json={"bio": "x" * 201})
    check("PATCH /users/{username} with bio > 200 chars returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # --- PATCH /posts/{id} — edit message ---
    # Create a post to edit
    r = c.post("/posts", json={"message": "original message"}, headers={"X-Username": ALICE})
    edit_post_id = None
    if r.status_code == 201:
        edit_post_id = r.json()["id"]

    if edit_post_id:
        # Author can edit
        r = c.patch(f"/posts/{edit_post_id}", json={"message": "edited message"}, headers={"X-Username": ALICE})
        check("PATCH /posts/{id} by author returns 200", r.status_code == 200, detail=f"got {r.status_code}")
        if r.status_code == 200:
            body = r.json()
            check("PATCH /posts/{id} response has updated message", body.get("message") == "edited message")
            check("PATCH /posts/{id} response has updated_at set", body.get("updated_at") is not None, detail=str(body))

        # Non-author gets 403
        r = c.patch(f"/posts/{edit_post_id}", json={"message": "hacked"}, headers={"X-Username": BOB})
        check("PATCH /posts/{id} by non-author returns 403", r.status_code == 403, detail=f"got {r.status_code}")

        # Missing X-Username returns 400
        r = c.patch(f"/posts/{edit_post_id}", json={"message": "no header"})
        check("PATCH /posts/{id} without X-Username returns 400", r.status_code == 400, detail=f"got {r.status_code}")

    # PATCH nonexistent post returns 404
    r = c.patch("/posts/99999999", json={"message": "nope"}, headers={"X-Username": ALICE})
    check("PATCH /posts/99999999 returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # PATCH with empty message returns 422
    if edit_post_id:
        r = c.patch(f"/posts/{edit_post_id}", json={"message": ""}, headers={"X-Username": ALICE})
        check("PATCH /posts/{id} with empty message returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # --- GET /posts?username=X filter ---
    r = c.get("/posts", params={"username": ALICE})
    check("GET /posts?username=ALICE returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        posts = r.json()
        check(
            "GET /posts?username=ALICE returns only ALICE's posts",
            all(p.get("username") == ALICE for p in posts) and len(posts) >= 1,
            detail=f"got {len(posts)} posts",
        )

    # Composable with ?q=
    needle = f"needle_{RUN}"
    r = c.get("/posts", params={"username": ALICE, "q": needle})
    check("GET /posts?username=ALICE&q=needle returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        posts = r.json()
        check(
            "GET /posts?username=ALICE&q=needle filters correctly",
            all(p.get("username") == ALICE and needle in p.get("message", "") for p in posts),
        )


# ======================================================================
# GOLD TIER CHECKS
# ======================================================================

def run_gold_checks(c: httpx.Client, state: dict) -> None:
    """Verify gold-tier features: cursor pagination, boards, feed, reactions."""
    print()
    print("--- Gold tier ---")

    # --- Cursor-based pagination ---
    r = c.get("/posts", params={"cursor": "", "limit": 2})
    # First call with empty cursor should fail or fallback; let's test with a real cursor
    # Get posts with regular pagination first to get an ID for cursor
    r = c.get("/posts", params={"limit": 3})
    if r.status_code == 200:
        posts = r.json()
        if len(posts) >= 2:
            # Use last post's ID to create a cursor
            import base64, json
            cursor_val = base64.urlsafe_b64encode(json.dumps({"id": posts[0]["id"]}).encode()).decode()
            r = c.get("/posts", params={"cursor": cursor_val, "limit": 2})
            check("GET /posts?cursor=... returns 200", r.status_code == 200, detail=f"got {r.status_code}")
            if r.status_code == 200:
                body = r.json()
                check(
                    "GET /posts?cursor=... returns envelope with posts and next_cursor",
                    isinstance(body, dict) and "posts" in body and "next_cursor" in body,
                    detail=str(type(body)),
                )
                check(
                    "Cursor pagination posts are a list",
                    isinstance(body.get("posts"), list),
                )
                # All returned posts should have ID < cursor_id
                if body.get("posts"):
                    check(
                        "Cursor pagination returns posts before cursor",
                        all(p["id"] < posts[0]["id"] for p in body["posts"]),
                        detail=f"cursor_id={posts[0]['id']}, got ids={[p['id'] for p in body['posts']]}",
                    )

    # --- Boards ---
    board_name = f"testboard_{RUN}"
    r = c.post("/boards", json={"name": board_name})
    check("POST /boards creates a board (201)", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        check("POST /boards response has name and created_at", "name" in body and "created_at" in body)

    # Duplicate board
    r = c.post("/boards", json={"name": board_name})
    check("POST /boards duplicate returns 409", r.status_code == 409, detail=f"got {r.status_code}")

    # List boards
    r = c.get("/boards")
    check("GET /boards returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        boards = r.json()
        board_names = [b["name"] for b in boards]
        check("GET /boards includes created board", board_name in board_names, detail=str(board_names))

    # GET /boards/{name}/posts on empty board
    r = c.get(f"/boards/{board_name}/posts")
    check(f"GET /boards/{board_name}/posts returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        check("GET /boards/{name}/posts returns empty list for new board", r.json() == [])

    # Nonexistent board
    r = c.get(f"/boards/doesnotexist_{RUN}/posts")
    check("GET /boards/nonexistent/posts returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # --- Feed ---
    r = c.get("/feed")
    check("GET /feed returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        feed_posts = r.json()
        check("GET /feed returns a list", isinstance(feed_posts, list))
        if len(feed_posts) >= 2:
            # Verify reverse chronological order
            check(
                "GET /feed is in reverse chronological order",
                feed_posts[0]["created_at"] >= feed_posts[1]["created_at"],
                detail=f"first={feed_posts[0]['created_at']}, second={feed_posts[1]['created_at']}",
            )

    # Feed with limit
    r = c.get("/feed", params={"limit": 2})
    check("GET /feed?limit=2 returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        check("GET /feed?limit=2 returns at most 2 items", len(r.json()) <= 2)

    # Feed with since
    r = c.get("/feed", params={"since": "2000-01-01T00:00:00"})
    check("GET /feed?since=... returns 200", r.status_code == 200, detail=f"got {r.status_code}")

    # --- Reactions ---
    # Use alice_post_id from earlier or create a new one
    react_post_id = state.get("alice_post_id")
    if not react_post_id:
        r = c.post("/posts", json={"message": "react to me"}, headers={"X-Username": ALICE})
        if r.status_code == 201:
            react_post_id = r.json()["id"]

    if react_post_id:
        # Add reaction
        r = c.post(f"/posts/{react_post_id}/reactions", json={"username": BOB, "kind": "+1"})
        check("POST /posts/{id}/reactions returns 201", r.status_code == 201, detail=f"got {r.status_code}")
        if r.status_code == 201:
            body = r.json()
            check(
                "POST /posts/{id}/reactions response has post_id, username, kind",
                body.get("post_id") == react_post_id and body.get("username") == BOB and body.get("kind") == "+1",
                detail=str(body),
            )

        # Duplicate reaction returns 409
        r = c.post(f"/posts/{react_post_id}/reactions", json={"username": BOB, "kind": "+1"})
        check("POST /posts/{id}/reactions duplicate returns 409", r.status_code == 409, detail=f"got {r.status_code}")

        # Reaction on nonexistent post
        r = c.post("/posts/99999999/reactions", json={"username": BOB, "kind": "+1"})
        check("POST /posts/99999999/reactions returns 404", r.status_code == 404, detail=f"got {r.status_code}")

        # Reaction with nonexistent user
        r = c.post(f"/posts/{react_post_id}/reactions", json={"username": GHOST, "kind": "+1"})
        check("POST /posts/{id}/reactions with unknown user returns 404", r.status_code == 404, detail=f"got {r.status_code}")

        # Remove reaction
        r = c.delete(f"/posts/{react_post_id}/reactions/{BOB}")
        check("DELETE /posts/{id}/reactions/{username} returns 204", r.status_code == 204, detail=f"got {r.status_code}")

        # Remove nonexistent reaction
        r = c.delete(f"/posts/{react_post_id}/reactions/{BOB}")
        check("DELETE /posts/{id}/reactions/{username} already removed returns 404", r.status_code == 404, detail=f"got {r.status_code}")


if __name__ == "__main__":
    sys.exit(main())
