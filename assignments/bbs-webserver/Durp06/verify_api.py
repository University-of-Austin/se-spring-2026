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
"""

import base64
import json as _json
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

# Tier constant: "bronze", "silver", or "gold"
TIER = "gold"

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

    # Bronze TODOs implemented:
    run_delete_checks(c, state)
    run_pagination_checks(c, state)
    run_field_shape_checks(c, state)

    # Silver checks:
    run_silver_user_checks(c, state)
    run_silver_patch_post_checks(c, state)
    run_silver_filter_checks(c, state)

    # Gold checks:
    run_gold_cursor_checks(c, state)

    print()
    print(f"{PASSED} passed, {FAILED} failed")
    return 0 if FAILED == 0 else 1


def run_user_checks(c: httpx.Client, state: dict) -> None:
    r = c.post("/users", json={"username": ALICE})
    check("POST /users creates a user (201)", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        check(
            "POST /users response has username and created_at",
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
        expected_keys = {"id", "username", "message", "created_at"}
        check(
            "POST /posts response has id, username, message, created_at",
            expected_keys.issubset(set(body.keys())),
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


# ---------------------------------------------------------------------------
# Bronze TODOs
# ---------------------------------------------------------------------------

def run_delete_checks(c: httpx.Client, state: dict) -> None:
    """Bronze TODO #1: DELETE /posts/{id} behavior."""
    # Create a fresh post to delete
    r = c.post("/posts", json={"message": "delete me"}, headers={"X-Username": ALICE})
    check("run_delete_checks: create post returns 201",
          r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code != 201:
        return
    post_id = r.json()["id"]

    # DELETE returns 204
    r = c.delete(f"/posts/{post_id}")
    check("DELETE /posts/{id} returns 204", r.status_code == 204, detail=f"got {r.status_code}")

    # Subsequent GET returns 404
    r = c.get(f"/posts/{post_id}")
    check("GET /posts/{id} after DELETE returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # DELETE on non-existent id returns 404
    r = c.delete("/posts/99999999")
    check("DELETE /posts/99999999 returns 404", r.status_code == 404, detail=f"got {r.status_code}")


def run_pagination_checks(c: httpx.Client, state: dict) -> None:
    """Bronze TODO #2: ?limit= and ?offset= on GET /posts."""
    # Seed some posts
    for i in range(3):
        c.post("/posts", json={"message": f"paginate {i} {RUN}"}, headers={"X-Username": ALICE})

    # ?limit=2 returns at most 2 items
    r = c.get("/posts", params={"limit": 2})
    check("GET /posts?limit=2 returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        check("GET /posts?limit=2 returns at most 2 items",
              len(r.json()) <= 2, detail=f"got {len(r.json())}")

    # offset=1 returns different item than offset=0
    r0 = c.get("/posts", params={"limit": 1, "offset": 0})
    r1 = c.get("/posts", params={"limit": 1, "offset": 1})
    if r0.status_code == 200 and r1.status_code == 200 and r0.json() and r1.json():
        check("GET /posts?offset=1 skips first item",
              r0.json()[0]["id"] != r1.json()[0]["id"])

    # Validation errors
    r = c.get("/posts", params={"limit": 0})
    check("GET /posts?limit=0 returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.get("/posts", params={"limit": 500})
    check("GET /posts?limit=500 returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.get("/posts", params={"offset": -1})
    check("GET /posts?offset=-1 returns 422", r.status_code == 422, detail=f"got {r.status_code}")


def run_field_shape_checks(c: httpx.Client, state: dict) -> None:
    """Bronze/Silver TODO #3: exact response field shapes."""
    shape_user = f"shape_{RUN}"
    r = c.post("/users", json={"username": shape_user})
    check("run_field_shape_checks: create shape user returns 201",
          r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code != 201:
        return

    if TIER in ("silver", "gold"):
        expected_user_keys = {"username", "created_at", "bio", "post_count"}
        expected_post_keys = {"id", "username", "message", "created_at", "updated_at"}
    else:
        expected_user_keys = {"username", "created_at"}
        expected_post_keys = {"id", "username", "message", "created_at"}

    # POST /users shape
    body = r.json()
    check("POST /users response has exact user fields",
          set(body.keys()) == expected_user_keys, detail=str(set(body.keys())))

    # GET /users/{username} shape
    r = c.get(f"/users/{shape_user}")
    if r.status_code == 200:
        body = r.json()
        check("GET /users/{username} has exact user fields",
              set(body.keys()) == expected_user_keys, detail=str(set(body.keys())))

    # Items in GET /users shape
    r = c.get("/users")
    if r.status_code == 200 and r.json():
        item = r.json()[0]
        check("GET /users items have exact user fields",
              set(item.keys()) == expected_user_keys, detail=str(set(item.keys())))

    # POST /posts shape
    r = c.post("/posts", json={"message": "shape test"}, headers={"X-Username": shape_user})
    check("run_field_shape_checks: create shape post returns 201",
          r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        post_id = body["id"]
        check("POST /posts response has exact post fields",
              set(body.keys()) == expected_post_keys, detail=str(set(body.keys())))

        # GET /posts/{id} shape
        r = c.get(f"/posts/{post_id}")
        if r.status_code == 200:
            body = r.json()
            check("GET /posts/{id} has exact post fields",
                  set(body.keys()) == expected_post_keys, detail=str(set(body.keys())))

        # Items in GET /posts shape (bare array path)
        r = c.get("/posts")
        if r.status_code == 200:
            posts = r.json()
            if isinstance(posts, list) and posts:
                item = posts[0]
                check("GET /posts items have exact post fields",
                      set(item.keys()) == expected_post_keys, detail=str(set(item.keys())))


# ---------------------------------------------------------------------------
# Silver checks
# ---------------------------------------------------------------------------

def run_silver_user_checks(c: httpx.Client, state: dict) -> None:
    """Silver: bio + post_count + PATCH /users/{username}."""
    silver_user = f"silver_{RUN}"

    # Create with bio
    r = c.post("/users", json={"username": silver_user, "bio": "my bio"})
    check("Silver: POST /users with bio returns 201",
          r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        check("Silver: POST /users response includes bio",
              body.get("bio") == "my bio", detail=str(body))
        check("Silver: POST /users response includes post_count == 0",
              body.get("post_count") == 0, detail=str(body))

    # Create N posts and verify post_count
    n_posts = 3
    for i in range(n_posts):
        c.post("/posts", json={"message": f"silver post {i}"}, headers={"X-Username": silver_user})
    r = c.get(f"/users/{silver_user}")
    check(f"Silver: GET /users post_count == {n_posts} after {n_posts} posts",
          r.status_code == 200 and r.json().get("post_count") == n_posts,
          detail=str(r.json()) if r.status_code == 200 else f"status {r.status_code}")

    # PATCH /users/{username} happy path
    r = c.patch(f"/users/{silver_user}", json={"bio": "updated bio"})
    check("Silver: PATCH /users/{username} returns 200",
          r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        check("Silver: PATCH /users/{username} response has new bio",
              r.json().get("bio") == "updated bio", detail=str(r.json()))

    # PATCH on non-existent user -> 404
    r = c.patch(f"/users/{GHOST}", json={"bio": "x"})
    check("Silver: PATCH /users/{ghost} returns 404",
          r.status_code == 404, detail=f"got {r.status_code}")

    # PATCH with bio > 200 chars -> 422
    r = c.patch(f"/users/{silver_user}", json={"bio": "x" * 201})
    check("Silver: PATCH /users/{username} bio > 200 chars returns 422",
          r.status_code == 422, detail=f"got {r.status_code}")


def run_silver_patch_post_checks(c: httpx.Client, state: dict) -> None:
    """Silver: PATCH /posts/{id} ownership matrix."""
    author = f"patchauthor_{RUN}"
    other = f"patchother_{RUN}"
    c.post("/users", json={"username": author})
    c.post("/users", json={"username": other})
    r = c.post("/posts", json={"message": "original"}, headers={"X-Username": author})
    check("Silver: create post for PATCH returns 201",
          r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code != 201:
        return
    body = r.json()
    post_id = body["id"]
    created_at = body.get("created_at", "")

    # Verify updated_at present and equals created_at on create
    check("Silver: POST /posts response includes updated_at",
          "updated_at" in body, detail=str(body))
    check("Silver: POST /posts updated_at == created_at on create",
          body.get("updated_at") == created_at, detail=str(body))

    # PATCH happy path
    r = c.patch(f"/posts/{post_id}", json={"message": "patched"}, headers={"X-Username": author})
    check("Silver: PATCH /posts/{id} with correct X-Username returns 200",
          r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        patchbody = r.json()
        check("Silver: PATCH /posts response has updated message",
              patchbody.get("message") == "patched", detail=str(patchbody))
        check("Silver: PATCH /posts updated_at >= created_at",
              patchbody.get("updated_at", "") >= created_at, detail=str(patchbody))

    # PATCH without X-Username -> 400
    r = c.patch(f"/posts/{post_id}", json={"message": "no header"})
    check("Silver: PATCH /posts/{id} without X-Username returns 400",
          r.status_code == 400, detail=f"got {r.status_code}")

    # PATCH with different X-Username -> 403
    r = c.patch(f"/posts/{post_id}", json={"message": "wrong user"}, headers={"X-Username": other})
    check("Silver: PATCH /posts/{id} with wrong X-Username returns 403",
          r.status_code == 403, detail=f"got {r.status_code}")

    # PATCH on non-existent id -> 404
    r = c.patch("/posts/99999999", json={"message": "ghost"}, headers={"X-Username": author})
    check("Silver: PATCH /posts/99999999 returns 404",
          r.status_code == 404, detail=f"got {r.status_code}")

    # PATCH with empty message -> 422
    r = c.patch(f"/posts/{post_id}", json={"message": ""}, headers={"X-Username": author})
    check("Silver: PATCH /posts/{id} empty message returns 422",
          r.status_code == 422, detail=f"got {r.status_code}")


def run_silver_filter_checks(c: httpx.Client, state: dict) -> None:
    """Silver: ?username= filter on GET /posts."""
    filter_alice = f"filtalice_{RUN}"
    filter_bob = f"filtbob_{RUN}"
    c.post("/users", json={"username": filter_alice})
    c.post("/users", json={"username": filter_bob})
    c.post("/posts", json={"message": "alice filter 1"}, headers={"X-Username": filter_alice})
    c.post("/posts", json={"message": "alice filter 2"}, headers={"X-Username": filter_alice})
    c.post("/posts", json={"message": "bob filter"}, headers={"X-Username": filter_bob})

    # Filter by alice
    r = c.get("/posts", params={"username": filter_alice})
    check("Silver: GET /posts?username=alice returns 200",
          r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        posts = r.json()
        check("Silver: GET /posts?username=alice returns only alice posts",
              all(p.get("username") == filter_alice for p in posts) and len(posts) >= 2,
              detail=str(posts))

    # Filter by ghost -> 200 + empty array
    r = c.get("/posts", params={"username": GHOST})
    check("Silver: GET /posts?username=ghost returns 200",
          r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        check("Silver: GET /posts?username=ghost returns empty list",
              r.json() == [], detail=str(r.json()))

    # Compose with ?q=
    needle_msg = f"needle_filter_{RUN}"
    c.post("/posts", json={"message": f"alice has {needle_msg}"}, headers={"X-Username": filter_alice})
    r = c.get("/posts", params={"username": filter_alice, "q": needle_msg})
    check("Silver: GET /posts?username=alice&q=needle returns 200",
          r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        posts = r.json()
        check("Silver: ?username=alice&q=needle returns matching posts only",
              all(p.get("username") == filter_alice and needle_msg in p.get("message", "")
                  for p in posts) and len(posts) >= 1,
              detail=str(posts))


# ---------------------------------------------------------------------------
# Gold checks
# ---------------------------------------------------------------------------

def run_gold_cursor_checks(c: httpx.Client, state: dict) -> None:
    """Gold: cursor-based pagination roundtrip."""
    marker = f"cursor_marker_{RUN}"
    cursor_user = f"cursoruser_{RUN}"
    c.post("/users", json={"username": cursor_user})

    # Seed N=12 posts
    N = 12
    for i in range(N):
        c.post("/posts", json={"message": f"{marker} post {i}"}, headers={"X-Username": cursor_user})

    # Confirm bare array still works (bronze path preserved)
    r = c.get("/posts", params={"q": marker, "limit": 200})
    check("Gold: GET /posts (no cursor) returns bare list",
          r.status_code == 200 and isinstance(r.json(), list),
          detail=f"status={r.status_code}, type={type(r.json()).__name__}")
    seeded_posts = r.json()
    check(f"Gold: bare-array path returned all {N} seeded posts",
          len(seeded_posts) >= N, detail=f"got {len(seeded_posts)}")
    if len(seeded_posts) < 1:
        return
    all_ids = {p["id"] for p in seeded_posts}

    # Build initial cursor from id-1 of first seeded post
    first_id = min(all_ids)
    start_cursor = base64.urlsafe_b64encode(_json.dumps({"id": first_id - 1}).encode()).decode()

    # First cursor page
    limit = 5
    r = c.get("/posts", params={"q": marker, "cursor": start_cursor, "limit": limit})
    check("Gold: GET /posts?cursor=... returns 200",
          r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code != 200:
        return
    body = r.json()
    check("Gold: cursor response has 'posts' and 'next_cursor' keys",
          isinstance(body, dict) and "posts" in body and "next_cursor" in body,
          detail=str(type(body)) + (str(list(body.keys())) if isinstance(body, dict) else ""))
    if not (isinstance(body, dict) and "posts" in body):
        return
    check(f"Gold: first cursor page has {limit} posts",
          len(body["posts"]) == limit, detail=f"got {len(body['posts'])}")

    # Page through all cursor results
    accumulated_ids = {p["id"] for p in body["posts"]}
    current_cursor = body["next_cursor"]
    page_count = 1
    while current_cursor is not None and page_count < 20:
        r = c.get("/posts", params={"q": marker, "cursor": current_cursor, "limit": limit})
        check(f"Gold: cursor page {page_count + 1} returns 200",
              r.status_code == 200, detail=f"got {r.status_code}")
        if r.status_code != 200:
            break
        page_body = r.json()
        check(f"Gold: page {page_count + 1} has envelope shape",
              isinstance(page_body, dict) and "posts" in page_body and "next_cursor" in page_body,
              detail=str(page_body))
        if not isinstance(page_body, dict):
            break
        page_ids = {p["id"] for p in page_body["posts"]}
        check(f"Gold: no duplicate ids on page {page_count + 1}",
              len(accumulated_ids & page_ids) == 0,
              detail=f"overlap={accumulated_ids & page_ids}")
        accumulated_ids |= page_ids
        current_cursor = page_body["next_cursor"]
        page_count += 1

    check("Gold: final next_cursor is null",
          current_cursor is None, detail=f"got {current_cursor}")
    check("Gold: union of all cursor pages == all seeded ids",
          all_ids == accumulated_ids,
          detail=f"missing={all_ids - accumulated_ids}, extra={accumulated_ids - all_ids}")

    # Malformed cursor -> 422
    r = c.get("/posts", params={"cursor": "not-valid-base64!!!"})
    check("Gold: malformed cursor returns 422",
          r.status_code == 422, detail=f"got {r.status_code}")

    # Valid base64 of invalid JSON -> 422
    bad_json_cursor = base64.urlsafe_b64encode(b"not-json").decode()
    r = c.get("/posts", params={"cursor": bad_json_cursor})
    check("Gold: valid-b64 invalid-JSON cursor returns 422",
          r.status_code == 422, detail=f"got {r.status_code}")


if __name__ == "__main__":
    sys.exit(main())
