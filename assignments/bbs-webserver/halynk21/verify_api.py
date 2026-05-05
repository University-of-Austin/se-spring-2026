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
import sqlite3
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

    # ==================================================================
    # SILVER checks: PATCH /users, PATCH /posts, GET /posts?username=
    # Criteria: SI-03 through SI-15
    # ==================================================================
    run_silver_checks(c, state)

    # ==================================================================
    # GOLD checks: cursor pagination on GET /posts
    # Criteria: GO-01 through GO-08
    # ==================================================================
    run_gold_checks(c, state)

    # ==================================================================
    # GOLD checks: reactions
    # Criteria: GO-09 through GO-21
    # ==================================================================
    run_reaction_checks(c, state)

    print()
    print(f"{PASSED} passed, {FAILED} failed")
    return 0 if FAILED == 0 else 1


def run_user_checks(c: httpx.Client, state: dict) -> None:
    r = c.post("/users", json={"username": ALICE})
    check("POST /users creates a user (201)", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        check(
            "POST /users response has silver user shape {username, created_at, bio, post_count}",
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
            "POST /posts response has silver post shape {id, username, message, created_at, updated_at}",
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


# ==================================================================
# STUDENT TODO #1: DELETE /posts/{id}
# Criteria: BR-T1-a, BR-T1-b, BR-T1-c
# ==================================================================

def run_delete_checks(c: httpx.Client, state: dict) -> None:
    # Create a fresh post to delete so that alice_post_id remains available
    # for later checks (silver/gold may reference it via state).
    r = c.post(
        "/posts",
        json={"message": "delete me"},
        headers={"X-Username": ALICE},
    )
    if r.status_code != 201:
        check("BR-T1-a: DELETE /posts/<existing> returns 204", False,
              detail="could not create post to delete")
        check("BR-T1-b: after DELETE GET /posts/<id> returns 404", False,
              detail="could not create post to delete")
        check("BR-T1-c: DELETE /posts/99999999 returns 404", False,
              detail="skipped due to setup failure")
        return

    delete_id = r.json()["id"]

    # BR-T1-a: DELETE existing post returns 204
    r = c.delete(f"/posts/{delete_id}")
    check(
        "BR-T1-a: DELETE /posts/<existing> returns 204",
        r.status_code == 204,
        detail=f"got {r.status_code}",
    )

    # BR-T1-b: After DELETE, GET returns 404
    r = c.get(f"/posts/{delete_id}")
    check(
        "BR-T1-b: after DELETE GET /posts/<same-id> returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    # BR-T1-c: DELETE nonexistent post returns 404
    r = c.delete("/posts/99999999")
    check(
        "BR-T1-c: DELETE /posts/99999999 returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )


# ==================================================================
# STUDENT TODO #2: pagination on GET /posts
# Criteria: BR-T2-a, BR-T2-b, BR-T2-c, BR-T2-d, BR-T2-e
# ==================================================================

def run_pagination_checks(c: httpx.Client, state: dict) -> None:
    # BR-T2-a: limit=3 returns at most 3 items
    r = c.get("/posts", params={"limit": 3})
    check(
        "BR-T2-a: GET /posts?limit=3 returns at most 3 items",
        r.status_code == 200 and len(r.json()) <= 3,
        detail=f"status={r.status_code}, count={len(r.json()) if r.status_code == 200 else 'n/a'}",
    )

    # BR-T2-b: offset skips the first K items
    # Ground truth: fetch up to 10 results without offset
    r_full = c.get("/posts", params={"limit": 10})
    r_offset = c.get("/posts", params={"offset": 2, "limit": 10})
    if r_full.status_code == 200 and r_offset.status_code == 200:
        full_ids = [p["id"] for p in r_full.json()]
        offset_ids = [p["id"] for p in r_offset.json()]
        # The offset list should start where the full list starts at index 2
        expected_start = full_ids[2] if len(full_ids) > 2 else None
        actual_start = offset_ids[0] if offset_ids else None
        check(
            "BR-T2-b: GET /posts?offset=2&limit=10 skips first 2 items",
            expected_start is not None and actual_start == expected_start,
            detail=f"expected first id={expected_start}, got first id={actual_start}",
        )
    else:
        check(
            "BR-T2-b: GET /posts?offset=2&limit=10 skips first 2 items",
            False,
            detail=f"setup failed: full={r_full.status_code}, offset={r_offset.status_code}",
        )

    # BR-T2-c: limit=0 returns 422
    r = c.get("/posts", params={"limit": 0})
    check(
        "BR-T2-c: GET /posts?limit=0 returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # BR-T2-d: limit=500 returns 422 (above le=200)
    r = c.get("/posts", params={"limit": 500})
    check(
        "BR-T2-d: GET /posts?limit=500 returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # BR-T2-e: offset=-1 returns 422
    r = c.get("/posts", params={"offset": -1})
    check(
        "BR-T2-e: GET /posts?offset=-1 returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )


# ==================================================================
# STUDENT TODO #3: exact response field shapes
# Criteria: BR-T3-a (user shape), BR-T3-b (post shape)
# NOTE: Silver-extended shapes are used deliberately because this
# submission targets silver/gold. See README for rationale.
# User shape: {username, created_at, bio, post_count}
# Post shape: {id, username, message, created_at, updated_at}
# ==================================================================

EXPECTED_USER_KEYS = {"username", "created_at", "bio", "post_count"}
EXPECTED_POST_KEYS = {"id", "username", "message", "created_at", "updated_at"}


def run_field_shape_checks(c: httpx.Client, state: dict) -> None:
    # BR-T3-a: user shape from POST /users
    r = c.post("/users", json={"username": f"shape_{RUN}"})
    if r.status_code == 201:
        body = r.json()
        check(
            "BR-T3-a: POST /users response has silver user shape",
            set(body.keys()) == EXPECTED_USER_KEYS,
            detail=f"got {set(body.keys())}",
        )
    else:
        check(
            "BR-T3-a: POST /users response has silver user shape",
            False,
            detail=f"could not create user, status={r.status_code}",
        )

    # BR-T3-a: user shape from GET /users/{username}
    r = c.get(f"/users/{ALICE}")
    if r.status_code == 200:
        body = r.json()
        check(
            "BR-T3-a: GET /users/{username} response has silver user shape",
            set(body.keys()) == EXPECTED_USER_KEYS,
            detail=f"got {set(body.keys())}",
        )
    else:
        check(
            "BR-T3-a: GET /users/{username} response has silver user shape",
            False,
            detail=f"got {r.status_code}",
        )

    # BR-T3-a: user shape from items in GET /users
    r = c.get("/users")
    if r.status_code == 200:
        users = r.json()
        alice_items = [u for u in users if u.get("username") == ALICE]
        if alice_items:
            check(
                "BR-T3-a: GET /users items have silver user shape",
                set(alice_items[0].keys()) == EXPECTED_USER_KEYS,
                detail=f"got {set(alice_items[0].keys())}",
            )
        else:
            check(
                "BR-T3-a: GET /users items have silver user shape",
                False,
                detail=f"{ALICE} not found in GET /users response",
            )
    else:
        check(
            "BR-T3-a: GET /users items have silver user shape",
            False,
            detail=f"got {r.status_code}",
        )

    # BR-T3-b: post shape from POST /posts
    r = c.post(
        "/posts",
        json={"message": f"shape check post {RUN}"},
        headers={"X-Username": ALICE},
    )
    if r.status_code == 201:
        body = r.json()
        shape_post_id = body.get("id")
        state["shape_post_id"] = shape_post_id
        check(
            "BR-T3-b: POST /posts response has silver post shape",
            set(body.keys()) == EXPECTED_POST_KEYS,
            detail=f"got {set(body.keys())}",
        )
    else:
        shape_post_id = None
        check(
            "BR-T3-b: POST /posts response has silver post shape",
            False,
            detail=f"could not create post, status={r.status_code}",
        )

    # BR-T3-b: post shape from GET /posts/{id}
    if shape_post_id is not None:
        r = c.get(f"/posts/{shape_post_id}")
        if r.status_code == 200:
            body = r.json()
            check(
                "BR-T3-b: GET /posts/{id} response has silver post shape",
                set(body.keys()) == EXPECTED_POST_KEYS,
                detail=f"got {set(body.keys())}",
            )
        else:
            check(
                "BR-T3-b: GET /posts/{id} response has silver post shape",
                False,
                detail=f"got {r.status_code}",
            )
    else:
        check(
            "BR-T3-b: GET /posts/{id} response has silver post shape",
            False,
            detail="no post id available",
        )

    # BR-T3-b: post shape from items in GET /posts
    r = c.get("/posts", params={"limit": 10})
    if r.status_code == 200:
        posts = r.json()
        if posts:
            check(
                "BR-T3-b: GET /posts items have silver post shape",
                set(posts[0].keys()) == EXPECTED_POST_KEYS,
                detail=f"got {set(posts[0].keys())}",
            )
        else:
            check(
                "BR-T3-b: GET /posts items have silver post shape",
                False,
                detail="GET /posts returned empty list",
            )
    else:
        check(
            "BR-T3-b: GET /posts items have silver post shape",
            False,
            detail=f"got {r.status_code}",
        )


# ==================================================================
# SILVER checks
# Criteria: SI-03 through SI-15
# ==================================================================

def run_silver_checks(c: httpx.Client, state: dict) -> None:
    # SI-03: PATCH /users/{alice} with valid bio -> 200, silver user shape, bio updated
    r = c.patch(f"/users/{ALICE}", json={"bio": "wolf in dog suit"})
    check(
        "SI-03: PATCH /users/{alice} valid bio returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 200:
        body = r.json()
        check(
            "SI-03: PATCH /users/{alice} response has silver user shape",
            set(body.keys()) == EXPECTED_USER_KEYS,
            detail=f"got {set(body.keys())}",
        )
        check(
            "SI-03: PATCH /users/{alice} bio reflects new value",
            body.get("bio") == "wolf in dog suit",
            detail=f"got bio={body.get('bio')!r}",
        )

    # SI-04: PATCH /users/{ghost} -> 404
    r = c.patch(f"/users/{GHOST}", json={"bio": "nobody"})
    check(
        "SI-04: PATCH /users/{ghost} returns 404",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    # SI-05: PATCH /users/{alice} with bio > 200 chars -> 422
    r = c.patch(f"/users/{ALICE}", json={"bio": "x" * 201})
    check(
        "SI-05: PATCH /users/{alice} bio>200 chars returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # SI-06: PATCH /users/{alice} with {} -> 200 (no-op, bio unchanged)
    r_before = c.get(f"/users/{ALICE}")
    bio_before = r_before.json().get("bio") if r_before.status_code == 200 else None
    r = c.patch(f"/users/{ALICE}", json={})
    check(
        "SI-06: PATCH /users/{alice} empty body returns 200 (no-op)",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 200 and bio_before is not None:
        body = r.json()
        check(
            "SI-06: PATCH /users/{alice} empty body leaves bio unchanged",
            body.get("bio") == bio_before,
            detail=f"expected bio={bio_before!r}, got bio={body.get('bio')!r}",
        )

    # Create a fresh post for silver PATCH /posts tests so alice_post_id is not consumed
    r = c.post(
        "/posts",
        json={"message": "silver edit target"},
        headers={"X-Username": ALICE},
    )
    if r.status_code != 201:
        # All PATCH /posts checks depend on this; mark them failed and return early
        for label in [
            "SI-07: PATCH /posts/<id> valid edit returns 200",
            "SI-07: PATCH /posts/<id> response has silver post shape",
            "SI-07: PATCH /posts/<id> message reflects update",
            "SI-07: PATCH /posts/<id> updated_at is not None",
            "SI-08: PATCH /posts/99999999 returns 404",
            "SI-09: PATCH /posts/<id> wrong X-Username returns 403",
            "SI-10: PATCH /posts/<id> missing X-Username returns 400",
            "SI-11: PATCH /posts/<id> message>500 chars returns 422",
            "SI-12: PATCH /posts/<id> empty message returns 422",
        ]:
            check(label, False, detail="setup: could not create post for silver edit tests")
    else:
        silver_post_id = r.json()["id"]

        # SI-07: valid PATCH /posts/{id} with matching X-Username
        r = c.patch(
            f"/posts/{silver_post_id}",
            json={"message": "edited"},
            headers={"X-Username": ALICE},
        )
        check(
            "SI-07: PATCH /posts/<id> valid edit returns 200",
            r.status_code == 200,
            detail=f"got {r.status_code}",
        )
        if r.status_code == 200:
            body = r.json()
            check(
                "SI-07: PATCH /posts/<id> response has silver post shape",
                set(body.keys()) == EXPECTED_POST_KEYS,
                detail=f"got {set(body.keys())}",
            )
            check(
                "SI-07: PATCH /posts/<id> message reflects update",
                body.get("message") == "edited",
                detail=f"got message={body.get('message')!r}",
            )
            check(
                "SI-07: PATCH /posts/<id> updated_at is not None",
                body.get("updated_at") is not None,
                detail=f"got updated_at={body.get('updated_at')!r}",
            )
        else:
            check("SI-07: PATCH /posts/<id> response has silver post shape", False,
                  detail="skipped: edit did not return 200")
            check("SI-07: PATCH /posts/<id> message reflects update", False,
                  detail="skipped: edit did not return 200")
            check("SI-07: PATCH /posts/<id> updated_at is not None", False,
                  detail="skipped: edit did not return 200")

        # SI-08: PATCH /posts/99999999 -> 404
        r = c.patch(
            "/posts/99999999",
            json={"message": "no such post"},
            headers={"X-Username": ALICE},
        )
        check(
            "SI-08: PATCH /posts/99999999 returns 404",
            r.status_code == 404,
            detail=f"got {r.status_code}",
        )

        # SI-09: PATCH /posts/{id} with X-Username != author -> 403
        r = c.patch(
            f"/posts/{silver_post_id}",
            json={"message": "unauthorized edit"},
            headers={"X-Username": BOB},
        )
        check(
            "SI-09: PATCH /posts/<id> wrong X-Username returns 403",
            r.status_code == 403,
            detail=f"got {r.status_code}",
        )

        # SI-10: PATCH /posts/{id} with no X-Username header -> 400
        r = c.patch(
            f"/posts/{silver_post_id}",
            json={"message": "no header"},
        )
        check(
            "SI-10: PATCH /posts/<id> missing X-Username returns 400",
            r.status_code == 400,
            detail=f"got {r.status_code}",
        )

        # SI-11: PATCH /posts/{id} message > 500 chars -> 422
        r = c.patch(
            f"/posts/{silver_post_id}",
            json={"message": "x" * 501},
            headers={"X-Username": ALICE},
        )
        check(
            "SI-11: PATCH /posts/<id> message>500 chars returns 422",
            r.status_code == 422,
            detail=f"got {r.status_code}",
        )

        # SI-12: PATCH /posts/{id} empty message -> 422
        r = c.patch(
            f"/posts/{silver_post_id}",
            json={"message": ""},
            headers={"X-Username": ALICE},
        )
        check(
            "SI-12: PATCH /posts/<id> empty message returns 422",
            r.status_code == 422,
            detail=f"got {r.status_code}",
        )

    # SI-13: GET /posts?username=alice returns only alice's posts
    r = c.get("/posts", params={"username": ALICE})
    check(
        "SI-13: GET /posts?username=alice returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 200:
        posts = r.json()
        check(
            "SI-13: GET /posts?username=alice contains only alice posts",
            len(posts) >= 1 and all(p.get("username") == ALICE for p in posts),
            detail=f"usernames found: {list({p.get('username') for p in posts})}",
        )

    # SI-14: GET /posts?username=<nonexistent> returns 200 with empty array
    nonexistent = f"nobody_{RUN}"
    r = c.get("/posts", params={"username": nonexistent})
    check(
        "SI-14: GET /posts?username=<nonexistent> returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 200:
        check(
            "SI-14: GET /posts?username=<nonexistent> returns empty array",
            r.json() == [],
            detail=f"got {r.json()}",
        )

    # SI-15: composability — q + username + limit + offset
    silver_needle = f"silvr_{RUN}"
    c.post(
        "/posts",
        json={"message": f"silver composable post {silver_needle}"},
        headers={"X-Username": ALICE},
    )
    r = c.get(
        "/posts",
        params={"q": silver_needle, "username": ALICE, "limit": 10, "offset": 0},
    )
    check(
        "SI-15: GET /posts?q=<needle>&username=alice&limit=10&offset=0 returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 200:
        posts = r.json()
        check(
            "SI-15: composable result contains needle in every message",
            all(silver_needle in p.get("message", "") for p in posts) and len(posts) >= 1,
            detail=f"messages: {[p.get('message') for p in posts]}",
        )
        check(
            "SI-15: composable result contains only alice posts",
            all(p.get("username") == ALICE for p in posts),
            detail=f"usernames: {[p.get('username') for p in posts]}",
        )
        check(
            "SI-15: composable result contains at most 10 items",
            len(posts) <= 10,
            detail=f"got {len(posts)} items",
        )


# ==================================================================
# GOLD checks
# Criteria: GO-01 through GO-08
# ==================================================================

def _encode_cursor(post_id: int) -> str:
    """Encode a cursor the same way the server does: base64(json({"id": id}))."""
    payload = json.dumps({"id": post_id}).encode()
    return base64.urlsafe_b64encode(payload).decode()


def run_gold_checks(c: httpx.Client, state: dict) -> None:
    # Seed: ensure at least 12 posts exist so cursor pagination has multiple pages.
    for i in range(12):
        c.post(
            "/posts",
            json={"message": f"gold_{RUN}_{i}"},
            headers={"X-Username": ALICE},
        )

    # GO-07: GET /posts (no cursor) still returns a bare list
    r = c.get("/posts")
    check(
        "GO-07: GET /posts (no cursor) returns bare list",
        r.status_code == 200 and isinstance(r.json(), list),
        detail=f"status={r.status_code}, type={type(r.json()).__name__ if r.status_code == 200 else 'n/a'}",
    )

    # GO-08: GET /posts?offset=0&limit=5 still returns bare list with <= 5 items
    r = c.get("/posts", params={"offset": 0, "limit": 5})
    check(
        "GO-08: GET /posts?offset=0&limit=5 returns bare list",
        r.status_code == 200 and isinstance(r.json(), list),
        detail=f"status={r.status_code}, type={type(r.json()).__name__ if r.status_code == 200 else 'n/a'}",
    )
    if r.status_code == 200:
        check(
            "GO-08: GET /posts?offset=0&limit=5 has at most 5 items",
            len(r.json()) <= 5,
            detail=f"got {len(r.json())} items",
        )

    # Build a starting cursor by encoding a very large id so the server starts
    # from the newest posts and returns a real next_cursor.
    sentinel_cursor = _encode_cursor(10 ** 12)

    # GO-01: GET /posts?cursor=<valid> returns envelope with keys {posts, next_cursor}
    r = c.get("/posts", params={"cursor": sentinel_cursor, "limit": 5})
    check(
        "GO-01: GET /posts?cursor=<valid> returns 200",
        r.status_code == 200,
        detail=f"got {r.status_code}",
    )
    if r.status_code == 200:
        body = r.json()
        check(
            "GO-01: cursor response has keys {posts, next_cursor}",
            isinstance(body, dict) and set(body.keys()) == {"posts", "next_cursor"},
            detail=f"got {set(body.keys()) if isinstance(body, dict) else type(body).__name__}",
        )

        # GO-02: each item in posts has silver post shape
        posts_page1 = body.get("posts", [])
        if posts_page1:
            check(
                "GO-02: cursor page items have silver post shape",
                all(set(p.keys()) == EXPECTED_POST_KEYS for p in posts_page1),
                detail=f"first item keys: {set(posts_page1[0].keys()) if posts_page1 else 'empty'}",
            )
        else:
            check(
                "GO-02: cursor page items have silver post shape",
                False,
                detail="cursor page returned empty posts list",
            )

        # GO-03 and GO-04: walk all pages with cursor, verify no duplicates/gaps
        # Ground truth: fetch up to 200 posts via bare offset path
        r_ground = c.get("/posts", params={"limit": 200})
        ground_ids = [p["id"] for p in r_ground.json()] if r_ground.status_code == 200 else []

        # Walk cursor pages with limit=5
        collected_ids = []
        final_next_cursor = None
        cursor_val = sentinel_cursor
        for _page in range(50):  # safety cap
            r_page = c.get("/posts", params={"cursor": cursor_val, "limit": 5})
            if r_page.status_code != 200:
                break
            page_body = r_page.json()
            if not isinstance(page_body, dict):
                break
            page_posts = page_body.get("posts", [])
            collected_ids.extend(p["id"] for p in page_posts)
            final_next_cursor = page_body.get("next_cursor")
            if final_next_cursor is None:
                break
            cursor_val = final_next_cursor

        # GO-03: no duplicate ids in cursor walk
        check(
            "GO-03: cursor pagination has no duplicate post ids",
            len(collected_ids) == len(set(collected_ids)),
            detail=f"collected {len(collected_ids)} ids, {len(set(collected_ids))} unique",
        )

        # GO-03: cursor walk matches ground truth ordering (first N ids match).
        # Use min() so the check stays valid when the DB has more than 200
        # posts: ground_ids is capped at limit=200 but collected_ids walks all
        # pages, so comparing collected[:n] vs ground[:n] against the full
        # collected length would produce a false fail on a stale DB.
        if ground_ids and collected_ids:
            n = min(len(collected_ids), len(ground_ids))
            check(
                "GO-03: cursor-paged ids match ground-truth ordering",
                n > 0 and collected_ids[:n] == ground_ids[:n],
                detail=(
                    f"cursor ids (first 5): {collected_ids[:5]}, "
                    f"ground truth (first 5): {ground_ids[:5]}"
                ),
            )
        else:
            check(
                "GO-03: cursor-paged ids match ground-truth ordering",
                False,
                detail=f"ground_ids={len(ground_ids)}, collected_ids={len(collected_ids)}",
            )

        # GO-04: last page has next_cursor == None
        check(
            "GO-04: last cursor page has next_cursor == null",
            final_next_cursor is None,
            detail=f"got next_cursor={final_next_cursor!r}",
        )
    else:
        # Mark GO-02 through GO-04 as failed since setup did not succeed
        check("GO-02: cursor page items have silver post shape", False,
              detail="skipped: GO-01 did not return 200")
        check("GO-03: cursor pagination has no duplicate post ids", False,
              detail="skipped: GO-01 did not return 200")
        check("GO-03: cursor-paged ids match ground-truth ordering", False,
              detail="skipped: GO-01 did not return 200")
        check("GO-04: last cursor page has next_cursor == null", False,
              detail="skipped: GO-01 did not return 200")

    # GO-05: GET /posts?cursor=!!!not-base64!!! -> 422 (bad base64)
    r = c.get("/posts", params={"cursor": "!!!not-base64!!!"})
    check(
        "GO-05: GET /posts?cursor=!!!not-base64!!! returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )

    # GO-06: GET /posts?cursor=<base64 of garbage> -> 422 (decodes but not valid shape)
    garbage_cursor = base64.urlsafe_b64encode(b"garbage").decode()
    r = c.get("/posts", params={"cursor": garbage_cursor})
    check(
        "GO-06: GET /posts?cursor=<base64(garbage)> returns 422",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )


# ==================================================================
# GOLD checks: reactions
# Criteria: GO-09 through GO-21
# ==================================================================

def run_reaction_checks(c: httpx.Client, state: dict) -> None:
    r = c.post("/posts", json={"message": "reactable"}, headers={"X-Username": ALICE})
    if r.status_code != 201:
        check("GO-09: POST reaction returns 201", False, detail="setup: could not create post")
        return
    target_id = r.json()["id"]

    # GO-09: happy path — bob reacts with "like"
    r = c.post(f"/posts/{target_id}/reactions", json={"kind": "like"},
               headers={"X-Username": BOB})
    check("GO-09: POST reaction returns 201", r.status_code == 201,
          detail=f"got {r.status_code}")
    if r.status_code == 201:
        check("GO-09: reaction has shape {id, username, kind, created_at}",
              set(r.json().keys()) == {"id", "username", "kind", "created_at"},
              detail=str(r.json()))

    # GO-10: missing X-Username → 400
    check("GO-10: POST reaction missing X-Username returns 400",
          c.post(f"/posts/{target_id}/reactions", json={"kind": "fire"}).status_code == 400)

    # GO-11: unknown user → 404
    check("GO-11: POST reaction unknown user returns 404",
          c.post(f"/posts/{target_id}/reactions", json={"kind": "fire"},
                 headers={"X-Username": GHOST}).status_code == 404)

    # GO-12: missing post → 404
    check("GO-12: POST reaction on missing post returns 404",
          c.post("/posts/99999999/reactions", json={"kind": "fire"},
                 headers={"X-Username": BOB}).status_code == 404)

    # GO-13: invalid kind → 422
    check("GO-13: POST reaction invalid kind returns 422",
          c.post(f"/posts/{target_id}/reactions", json={"kind": "upvote"},
                 headers={"X-Username": BOB}).status_code == 422)

    # GO-14: duplicate reaction → 409
    check("GO-14: duplicate reaction returns 409",
          c.post(f"/posts/{target_id}/reactions", json={"kind": "like"},
                 headers={"X-Username": BOB}).status_code == 409)

    # GO-15: different kind same user → 201
    check("GO-15: different kind same user returns 201",
          c.post(f"/posts/{target_id}/reactions", json={"kind": "fire"},
                 headers={"X-Username": BOB}).status_code == 201)

    # GO-16: aggregate counts (bob: like+fire, alice: like → {like:2, fire:1}, total:3)
    c.post(f"/posts/{target_id}/reactions", json={"kind": "like"},
           headers={"X-Username": ALICE})
    r = c.get(f"/posts/{target_id}/reactions")
    check("GO-16: aggregate counts correct",
          r.status_code == 200
          and r.json().get("by_kind") == {"like": 2, "fire": 1}
          and r.json().get("total") == 3,
          detail=str(r.json() if r.status_code == 200 else r.status_code))

    # GO-17: empty reactions on a fresh post
    empty_id = c.post("/posts", json={"message": "unreacted"},
                      headers={"X-Username": ALICE}).json()["id"]
    r = c.get(f"/posts/{empty_id}/reactions")
    check("GO-17: empty reactions returns total=0, by_kind={}, reactions=[]",
          r.status_code == 200
          and r.json() == {"total": 0, "by_kind": {}, "reactions": []},
          detail=str(r.json() if r.status_code == 200 else r.status_code))

    # GO-18: GET reactions on missing post → 404
    check("GO-18: GET reactions on missing post returns 404",
          c.get("/posts/99999999/reactions").status_code == 404)

    # GO-19: DELETE 204, then second DELETE → 404
    r = c.delete(f"/posts/{target_id}/reactions/fire", headers={"X-Username": BOB})
    check("GO-19: DELETE reaction returns 204", r.status_code == 204,
          detail=f"got {r.status_code}")
    r = c.delete(f"/posts/{target_id}/reactions/fire", headers={"X-Username": BOB})
    check("GO-19: second DELETE returns 404", r.status_code == 404,
          detail=f"got {r.status_code}")

    # GO-20: DELETE missing X-Username → 400
    check("GO-20: DELETE reaction missing X-Username returns 400",
          c.delete(f"/posts/{target_id}/reactions/like").status_code == 400)

    # GO-21: ON DELETE CASCADE — reactions are removed when the parent post is deleted.
    # Verified by opening a direct sqlite3 connection so the cascade is observable
    # even though the API surface has no endpoint that would expose orphan reactions.
    cascade_post = c.post("/posts", json={"message": "doomed"},
                          headers={"X-Username": ALICE}).json()["id"]
    c.post(f"/posts/{cascade_post}/reactions", json={"kind": "heart"},
           headers={"X-Username": BOB})
    c.delete(f"/posts/{cascade_post}")

    con = sqlite3.connect("bbs.db")
    try:
        orphans = con.execute(
            "SELECT COUNT(*) FROM reactions WHERE post_id = ?", (cascade_post,)
        ).fetchone()[0]
    finally:
        con.close()
    check("GO-21: ON DELETE CASCADE removes reactions with parent post",
          orphans == 0, detail=f"found {orphans} orphan reactions")


if __name__ == "__main__":
    sys.exit(main())
