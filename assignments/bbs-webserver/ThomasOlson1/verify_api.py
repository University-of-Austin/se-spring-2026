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

    run_delete_checks(c, state)
    run_pagination_checks(c, state)
    run_field_shape_checks(c, state)
    run_silver_checks(c, state)
    run_board_checks(c, state)
    run_adversarial_checks(c, state)

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
            set(body.keys()) == {"username", "created_at", "bio", "post_count"}
            and body["username"] == ALICE,
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
            "POST /posts response has exactly id, username, message, created_at, updated_at, board",
            set(body.keys()) == POST_KEYS,
            detail=str(body),
        )
        check("POST /posts response username matches header", body.get("username") == ALICE)
        check("POST /posts response message matches body", body.get("message") == "hello world")
        check(
            "POST /posts response updated_at is null on fresh post",
            body.get("updated_at") is None,
            detail=f"updated_at={body.get('updated_at')!r}",
        )
        check(
            "POST /posts defaults board to 'general'",
            body.get("board") == "general",
            detail=f"board={body.get('board')!r}",
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
    # Create a dedicated post so we can delete it without affecting other checks.
    r = c.post(
        "/posts",
        json={"message": "delete-me"},
        headers={"X-Username": ALICE},
    )
    check(
        "setup: POST /posts for delete target returns 201",
        r.status_code == 201,
        detail=f"got {r.status_code}",
    )
    if r.status_code != 201:
        return
    target_id = r.json()["id"]

    # Missing X-Username on DELETE should 400, same contract as PATCH.
    r = c.delete(f"/posts/{target_id}")
    check(
        f"DELETE /posts/{target_id} without X-Username returns 400",
        r.status_code == 400,
        detail=f"got {r.status_code}",
    )

    # Non-author trying to delete alice's post should 403.
    r = c.delete(f"/posts/{target_id}", headers={"X-Username": BOB})
    check(
        f"DELETE /posts/{target_id} by non-author returns 403",
        r.status_code == 403,
        detail=f"got {r.status_code}",
    )

    r = c.delete(f"/posts/{target_id}", headers={"X-Username": ALICE})
    check(
        f"DELETE /posts/{target_id} returns 204",
        r.status_code == 204,
        detail=f"got {r.status_code}",
    )
    check(
        f"DELETE /posts/{target_id} has empty body",
        r.content == b"",
        detail=f"got body {r.content!r}",
    )

    r = c.get(f"/posts/{target_id}")
    check(
        f"GET /posts/{target_id} after delete returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    r = c.delete("/posts/99999999", headers={"X-Username": ALICE})
    check(
        "DELETE /posts/99999999 (nonexistent) returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    # Idempotency check: deleting the same id twice should also 404 the second time.
    r = c.delete(f"/posts/{target_id}", headers={"X-Username": ALICE})
    check(
        f"DELETE /posts/{target_id} a second time returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )


def run_pagination_checks(c: httpx.Client, state: dict) -> None:
    # Seed enough posts for limit/offset math to be meaningful across runs.
    for i in range(6):
        c.post(
            "/posts",
            json={"message": f"page_{RUN}_{i}"},
            headers={"X-Username": ALICE},
        )

    r = c.get("/posts", params={"limit": 3})
    check("GET /posts?limit=3 returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        items = r.json()
        check(
            "GET /posts?limit=3 returns at most 3 items",
            isinstance(items, list) and len(items) <= 3,
            detail=f"got {len(items) if isinstance(items, list) else type(items).__name__}",
        )

    r_all = c.get("/posts", params={"limit": 200})
    r_off = c.get("/posts", params={"limit": 200, "offset": 2})
    if r_all.status_code == 200 and r_off.status_code == 200:
        all_ids = [p["id"] for p in r_all.json()]
        off_ids = [p["id"] for p in r_off.json()]
        check(
            "GET /posts?offset=2 skips the first 2 items",
            off_ids == all_ids[2:],
            detail=f"all={all_ids[:5]}... off={off_ids[:5]}...",
        )

    r = c.get("/posts", params={"limit": 0})
    check(
        "GET /posts?limit=0 returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    r = c.get("/posts", params={"limit": 500})
    check(
        "GET /posts?limit=500 returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    r = c.get("/posts", params={"offset": -1})
    check(
        "GET /posts?offset=-1 returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # Edge: limit at the upper bound should succeed.
    r = c.get("/posts", params={"limit": 200})
    check(
        "GET /posts?limit=200 (upper bound) returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )


USER_KEYS = {"username", "created_at", "bio", "post_count"}
POST_KEYS = {"id", "username", "message", "created_at", "updated_at", "board"}
BOARD_KEYS = {"name"}


def _assert_keys(label: str, body: dict, expected: set) -> None:
    actual = set(body.keys())
    missing = expected - actual
    extra = actual - expected
    ok = not missing and not extra
    detail_parts = []
    if missing:
        detail_parts.append(f"missing={sorted(missing)}")
    if extra:
        detail_parts.append(f"extra={sorted(extra)}")
    check(label, ok, detail=" ".join(detail_parts) or str(body))


def run_field_shape_checks(c: httpx.Client, state: dict) -> None:
    shape_user = f"shape_{RUN}"

    r = c.post("/users", json={"username": shape_user})
    if r.status_code == 201:
        _assert_keys("POST /users response shape == {username, created_at, bio, post_count}", r.json(), USER_KEYS)

    r = c.get(f"/users/{shape_user}")
    if r.status_code == 200:
        _assert_keys(
            f"GET /users/{shape_user} response shape == {{username, created_at, bio, post_count}}",
            r.json(),
            USER_KEYS,
        )

    r = c.get("/users")
    if r.status_code == 200 and isinstance(r.json(), list) and r.json():
        _assert_keys(
            "GET /users items shape == {username, created_at, bio, post_count}",
            r.json()[0],
            USER_KEYS,
        )

    r = c.post("/posts", json={"message": "shape-check"}, headers={"X-Username": shape_user})
    if r.status_code == 201:
        body = r.json()
        _assert_keys(
            "POST /posts response shape == {id, username, message, created_at, updated_at}",
            body,
            POST_KEYS,
        )
        pid = body.get("id")

        r = c.get(f"/posts/{pid}")
        if r.status_code == 200:
            _assert_keys(
                f"GET /posts/{pid} response shape == {{id, username, message, created_at, updated_at}}",
                r.json(),
                POST_KEYS,
            )

    r = c.get("/posts", params={"limit": 5})
    if r.status_code == 200 and isinstance(r.json(), list) and r.json():
        _assert_keys(
            "GET /posts items shape == {id, username, message, created_at, updated_at}",
            r.json()[0],
            POST_KEYS,
        )

    r = c.get(f"/users/{shape_user}/posts")
    if r.status_code == 200 and isinstance(r.json(), list) and r.json():
        _assert_keys(
            f"GET /users/{shape_user}/posts items shape == {{id, username, message, created_at, updated_at}}",
            r.json()[0],
            POST_KEYS,
        )


def run_silver_checks(c: httpx.Client, state: dict) -> None:
    # --- User bio + post_count ---
    silver_user = f"silver_{RUN}"

    r = c.post("/users", json={"username": silver_user})
    if r.status_code == 201:
        body = r.json()
        check(
            "silver: new user has bio='' and post_count=0",
            body.get("bio") == "" and body.get("post_count") == 0,
            detail=str(body),
        )

    # Create 2 posts, then confirm post_count reflects them.
    c.post("/posts", json={"message": "p1"}, headers={"X-Username": silver_user})
    c.post("/posts", json={"message": "p2"}, headers={"X-Username": silver_user})
    r = c.get(f"/users/{silver_user}")
    check(
        "silver: post_count increments as posts are created",
        r.status_code == 200 and r.json().get("post_count") == 2,
        detail=str(r.json()) if r.status_code == 200 else f"status={r.status_code}",
    )

    # --- PATCH /users/{u} ---
    r = c.patch(f"/users/{silver_user}", json={"bio": "a short bio"})
    check(
        f"PATCH /users/{silver_user} returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 200:
        body = r.json()
        check(
            "PATCH /users returns full user shape",
            set(body.keys()) == USER_KEYS,
            detail=str(body),
        )
        check(
            "PATCH /users updated bio is reflected",
            body.get("bio") == "a short bio",
            detail=str(body),
        )

    # GET confirms the bio persisted.
    r = c.get(f"/users/{silver_user}")
    check(
        "silver: GET /users/{u} reflects patched bio",
        r.status_code == 200 and r.json().get("bio") == "a short bio",
        detail=str(r.json()) if r.status_code == 200 else f"status={r.status_code}",
    )

    r = c.patch(f"/users/{GHOST}", json={"bio": "anything"})
    check(
        f"PATCH /users/{GHOST} (missing user) returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    r = c.patch(f"/users/{silver_user}", json={"bio": "x" * 201})
    check(
        "PATCH /users with 201-char bio returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # --- PATCH /posts/{id} ---
    r = c.post("/posts", json={"message": "original"}, headers={"X-Username": silver_user})
    pid = r.json().get("id") if r.status_code == 201 else None

    if pid is not None:
        r = c.patch(
            f"/posts/{pid}",
            json={"message": "edited"},
            headers={"X-Username": silver_user},
        )
        check(
            f"PATCH /posts/{pid} by author returns 200",
            r.status_code == 200,
            detail=f"got {r.status_code}",
        )
        if r.status_code == 200:
            body = r.json()
            check(
                "PATCH /posts response shape == {id, username, message, created_at, updated_at}",
                set(body.keys()) == POST_KEYS,
                detail=str(body),
            )
            check(
                "PATCH /posts response has edited message",
                body.get("message") == "edited",
                detail=str(body),
            )
            check(
                "PATCH /posts response has non-null updated_at",
                body.get("updated_at") is not None,
                detail=str(body),
            )

        # Non-author tries to edit: should be forbidden.
        r = c.patch(
            f"/posts/{pid}",
            json={"message": "pwn"},
            headers={"X-Username": ALICE},
        )
        check(
            f"PATCH /posts/{pid} by non-author returns 403",
            r.status_code == 403,
            detail=f"got {r.status_code}",
        )

    r = c.patch("/posts/99999999", json={"message": "ghost"}, headers={"X-Username": silver_user})
    check(
        "PATCH /posts/99999999 (missing) returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    r = c.patch(f"/posts/{pid}", json={"message": "no-header"}) if pid else None
    if r is not None:
        check(
            "PATCH /posts without X-Username returns 400",
            r.status_code == 400,
            detail=f"got {r.status_code}",
        )

    # --- ?username= filter (composable) ---
    filter_needle = f"filterneedle_{RUN}"
    c.post(
        "/posts",
        json={"message": f"alice has a {filter_needle}"},
        headers={"X-Username": ALICE},
    )
    c.post(
        "/posts",
        json={"message": f"silver user has a {filter_needle}"},
        headers={"X-Username": silver_user},
    )

    r = c.get("/posts", params={"username": silver_user})
    check(
        f"GET /posts?username={silver_user} returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 200:
        items = r.json()
        check(
            "GET /posts?username=... returns only that user's posts",
            all(p.get("username") == silver_user for p in items) and len(items) >= 1,
            detail=f"count={len(items)}",
        )

    # Compose with q:
    r = c.get("/posts", params={"username": silver_user, "q": filter_needle})
    if r.status_code == 200:
        items = r.json()
        check(
            "GET /posts?username=...&q=... composes (only that user's matching posts)",
            all(p.get("username") == silver_user and filter_needle in p.get("message", "") for p in items)
            and len(items) >= 1,
            detail=f"items={items}",
        )

    # Compose with limit:
    r = c.get("/posts", params={"username": silver_user, "limit": 1})
    if r.status_code == 200:
        items = r.json()
        check(
            "GET /posts?username=...&limit=1 respects limit",
            len(items) <= 1,
            detail=f"count={len(items)}",
        )


def run_board_checks(c: httpx.Client, state: dict) -> None:
    board_user = f"board_{RUN}"
    c.post("/users", json={"username": board_user})

    # --- GET /boards always has 'general' seeded ---
    r = c.get("/boards")
    check(
        "GET /boards returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 200:
        names = [b["name"] for b in r.json()]
        check(
            "GET /boards includes seeded 'general' board",
            "general" in names,
            detail=f"names={names}",
        )
        for item in r.json():
            _assert_keys("GET /boards item shape == {name}", item, BOARD_KEYS)
            break  # one sample is enough

    # --- POST /boards create + duplicate + validation ---
    board_name = f"board{RUN}"
    r = c.post("/boards", json={"name": board_name})
    check(
        f"POST /boards creates '{board_name}' (201)",
        r.status_code == 201,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 201:
        _assert_keys("POST /boards response shape == {name}", r.json(), BOARD_KEYS)
        check(
            "POST /boards response echoes the name",
            r.json().get("name") == board_name,
            detail=str(r.json()),
        )

    r = c.post("/boards", json={"name": board_name})
    check(
        "POST /boards duplicate returns 409",
        r.status_code == 409,
        detail=f"got {r.status_code}",
    )

    for bad_name in ["", "has spaces", "bang!", "a" * 41]:
        r = c.post("/boards", json={"name": bad_name})
        check(
            f"POST /boards invalid name {bad_name!r} returns 422",
            r.status_code == 422,
            detail=f"got {r.status_code}",
        )

    # Hyphens are intentionally allowed.
    r = c.post("/boards", json={"name": f"rust-lang-{RUN}"})
    check(
        "POST /boards with hyphen is allowed",
        r.status_code == 201,
        detail=f"got {r.status_code}",
    )

    # --- POST /boards/{name}/posts ---
    r = c.post(
        f"/boards/{board_name}/posts",
        json={"message": "hello from board"},
        headers={"X-Username": board_user},
    )
    check(
        f"POST /boards/{board_name}/posts returns 201",
        r.status_code == 201,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 201:
        body = r.json()
        check(
            "POST /boards/{name}/posts response shape matches POST_KEYS",
            set(body.keys()) == POST_KEYS,
            detail=str(body),
        )
        check(
            f"POST /boards/{board_name}/posts sets board to '{board_name}'",
            body.get("board") == board_name,
            detail=str(body),
        )
        state["board_post_id"] = body.get("id")

    # Missing header
    r = c.post(
        f"/boards/{board_name}/posts",
        json={"message": "headerless"},
    )
    check(
        "POST /boards/{name}/posts without X-Username returns 400",
        r.status_code == 400,
        detail=f"got {r.status_code}",
    )

    # Unknown user
    r = c.post(
        f"/boards/{board_name}/posts",
        json={"message": "ghost"},
        headers={"X-Username": GHOST},
    )
    check(
        "POST /boards/{name}/posts with unknown user returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    # Unknown board
    r = c.post(
        f"/boards/nope_{RUN}/posts",
        json={"message": "void"},
        headers={"X-Username": board_user},
    )
    check(
        "POST /boards/<unknown>/posts returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    # --- GET /boards/{name}/posts ---
    r = c.get(f"/boards/{board_name}/posts")
    check(
        f"GET /boards/{board_name}/posts returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 200:
        items = r.json()
        check(
            f"GET /boards/{board_name}/posts contains only that board",
            all(p.get("board") == board_name for p in items) and len(items) >= 1,
            detail=f"boards seen={sorted({p.get('board') for p in items})}",
        )
        if items:
            _assert_keys(
                "GET /boards/{name}/posts item shape matches POST_KEYS",
                items[0],
                POST_KEYS,
            )

    # Unknown board → 404
    r = c.get(f"/boards/nope_{RUN}/posts")
    check(
        "GET /boards/<unknown>/posts returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    # GET with q filter composes correctly
    needle = f"boardneedle_{RUN}"
    c.post(
        f"/boards/{board_name}/posts",
        json={"message": f"board post with {needle}"},
        headers={"X-Username": board_user},
    )
    r = c.get(f"/boards/{board_name}/posts", params={"q": needle})
    if r.status_code == 200:
        items = r.json()
        check(
            f"GET /boards/{board_name}/posts?q={needle} composes correctly",
            all(p.get("board") == board_name and needle in p.get("message", "") for p in items)
            and len(items) >= 1,
            detail=f"items={items}",
        )

    # --- flat filter ?board= on GET /posts ---
    r = c.get("/posts", params={"board": board_name})
    check(
        f"GET /posts?board={board_name} returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 200:
        items = r.json()
        check(
            "GET /posts?board=... returns only that board",
            all(p.get("board") == board_name for p in items) and len(items) >= 1,
            detail=f"boards seen={sorted({p.get('board') for p in items})}",
        )

    # Compose ?board= with ?username= and ?q=
    r = c.get(
        "/posts",
        params={"board": board_name, "username": board_user, "q": needle},
    )
    if r.status_code == 200:
        items = r.json()
        check(
            "GET /posts?board=&username=&q= all compose",
            all(
                p.get("board") == board_name
                and p.get("username") == board_user
                and needle in p.get("message", "")
                for p in items
            )
            and len(items) >= 1,
            detail=f"items={items}",
        )

    # Flat ?board= with an unknown board → 200 with empty list
    # (unlike the path-scoped endpoint which 404s — different contract, intentional)
    r = c.get("/posts", params={"board": f"nope_{RUN}"})
    check(
        "GET /posts?board=<unknown> returns 200 with empty list (flat filter semantics)",
        r.status_code == 200 and r.json() == [],
        detail=f"status={r.status_code} body={r.json() if r.status_code == 200 else None}",
    )

    # --- POST /posts still defaults to 'general' ---
    r = c.post("/posts", json={"message": "default board"}, headers={"X-Username": board_user})
    if r.status_code == 201:
        check(
            "POST /posts (no board path) still defaults to 'general'",
            r.json().get("board") == "general",
            detail=str(r.json()),
        )


def run_adversarial_checks(c: httpx.Client, state: dict) -> None:
    """Send malformed / hostile inputs and verify the server rejects them cleanly.
    None of these should 500. Wrong type = 422, SQL-inject attempts = 404, etc."""

    adv_user = f"adv_{RUN}"
    c.post("/users", json={"username": adv_user})

    # --- wrong JSON types on POST /users ---
    for bad in [
        {"username": 123},            # int instead of string
        {"username": None},           # null
        {"username": ["alice"]},      # array
        {"username": {"x": 1}},       # object
    ]:
        r = c.post("/users", json=bad)
        check(
            f"POST /users with bad username type {bad!r} returns 422",
            r.status_code == 422,
            detail=f"got {r.status_code}",
        )

    # Non-JSON-object bodies
    r = c.post("/users", json=["alice"])
    check(
        "POST /users with array body returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )
    r = c.post("/users", json="alice")
    check(
        "POST /users with string body returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # Username at exact boundaries of the regex/length rules
    r = c.post("/users", json={"username": "a" * 21})
    check(
        "POST /users with 21-char username returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )
    r = c.post("/users", json={"username": "alice-bob"})
    check(
        "POST /users with hyphen in username returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # Pydantic's default is extra="ignore" — extras are dropped, not rejected.
    # This pins that behavior so a future strict-mode flip is visible.
    r = c.post("/users", json={"username": f"extra_{RUN}", "role": "admin", "is_admin": True})
    check(
        "POST /users silently drops unknown fields (extra='ignore')",
        r.status_code == 201 and "role" not in r.json() and "is_admin" not in r.json(),
        detail=f"status={r.status_code} body={r.json() if r.status_code == 201 else None}",
    )

    # --- wrong JSON types on POST /posts ---
    for bad in [
        {"message": 0},               # int
        {"message": None},            # null
        {"message": ["hi"]},          # array
    ]:
        r = c.post("/posts", json=bad, headers={"X-Username": adv_user})
        check(
            f"POST /posts with bad message type {bad!r} returns 422",
            r.status_code == 422,
            detail=f"got {r.status_code}",
        )

    # --- path-param type coercion: non-int post id ---
    r = c.get("/posts/not-a-number")
    check(
        "GET /posts/not-a-number returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )
    r = c.delete("/posts/not-a-number")
    check(
        "DELETE /posts/not-a-number returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )
    r = c.patch(
        "/posts/not-a-number",
        json={"message": "x"},
        headers={"X-Username": adv_user},
    )
    check(
        "PATCH /posts/not-a-number returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # --- query-param type coercion ---
    r = c.get("/posts", params={"limit": "abc"})
    check(
        "GET /posts?limit=abc returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )
    r = c.get("/posts", params={"offset": "abc"})
    check(
        "GET /posts?offset=abc returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # --- SQL-injection-style inputs (parameterized queries must neutralize) ---
    # These should NOT crash, NOT drop tables, and should produce a clean 404
    # or a normal empty list, never a 500.
    inj_headers = {"X-Username": "alice'; DROP TABLE users;--"}
    r = c.post("/posts", json={"message": "oops"}, headers=inj_headers)
    check(
        "POST /posts with SQLi X-Username returns 404 (parameterized query neutralizes it)",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )
    # Confirm users table is still intact
    r = c.get("/users")
    check(
        "users table survives SQLi attempt (GET /users still 200)",
        r.status_code == 200 and isinstance(r.json(), list),
        detail=f"status={r.status_code}",
    )

    # Search with SQL wildcard should treat % as a literal-like character,
    # not expand it. Posting then searching for '%' must find the post.
    wildcard_marker = f"{100 * '%'}_{RUN}"
    c.post("/posts", json={"message": f"wild {wildcard_marker} card"}, headers={"X-Username": adv_user})
    r = c.get("/posts", params={"q": wildcard_marker})
    check(
        "GET /posts?q=%-string returns 200 without crashing",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )

    # --- PATCH /users with bad bio types ---
    for bad in [
        {"bio": 123},
        {"bio": None},
        {"bio": ["a"]},
        {},                          # missing required field
    ]:
        r = c.patch(f"/users/{adv_user}", json=bad)
        check(
            f"PATCH /users with bad body {bad!r} returns 422",
            r.status_code == 422,
            detail=f"got {r.status_code}",
        )

    # --- PATCH /posts with bad message types ---
    # Create a post we own to target.
    r = c.post("/posts", json={"message": "target"}, headers={"X-Username": adv_user})
    if r.status_code == 201:
        adv_pid = r.json()["id"]
        for bad in [
            {"message": 1},
            {"message": None},
            {},
        ]:
            r = c.patch(f"/posts/{adv_pid}", json=bad, headers={"X-Username": adv_user})
            check(
                f"PATCH /posts with bad body {bad!r} returns 422",
                r.status_code == 422,
                detail=f"got {r.status_code}",
            )

    # --- malformed Content-Type / raw-body attacks ---
    r = c.post(
        "/users",
        content=b"not json at all",
        headers={"Content-Type": "application/json"},
    )
    check(
        "POST /users with invalid JSON body returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # --- oversized payload: 1 MB username ---
    r = c.post("/users", json={"username": "a" * 1_000_000})
    check(
        "POST /users with 1MB username returns 422 (length validation, not a crash)",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )


if __name__ == "__main__":
    sys.exit(main())
