"""verify_api.py - conformance check for the BBS webserver.

HOW TO USE:
  1. Start your server:   uvicorn main:app --port 8000
  2. In another shell:    python verify_api.py
  3. Read the output. Fix any FAIL lines. Repeat.

This script uses random usernames on every run, so it does NOT require
a clean database. You can run it over and over against the same server.
If you want to start fresh, stop your server, delete bbs.db, and restart.

Student-added sections for this submission:
  - run_delete_checks        (bronze TODO #1)
  - run_pagination_checks    (bronze TODO #2)
  - run_field_shape_checks   (bronze TODO #3, asserts gold shape)
  - run_patch_user_checks    (silver)
  - run_patch_post_checks    (silver, ownership policy = author-only)
  - run_filter_by_username_checks  (silver)
  - run_reaction_checks      (gold)

The shipped bronze field-shape assertions on POST /users and POST /posts
have been updated from the bare bronze shape to the gold shape this
submission actually returns: users include {bio, post_count}, posts
include {updated_at, reactions}. Without that tweak the bronze checks
would (correctly) flag the extra silver/gold fields.
"""

import os
import sys
import uuid

import httpx

BASE = os.environ.get("BBS_BASE", "http://localhost:8000")

RUN = uuid.uuid4().hex[:8]
ALICE = f"alice_{RUN}"
BOB = f"bob_{RUN}"
CAROL = f"carol_{RUN}"
GHOST = f"ghost_{RUN}"  # never created

USER_KEYS = {"username", "created_at", "bio", "post_count"}
POST_KEYS = {"id", "username", "message", "created_at", "updated_at", "reactions"}

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

    state: dict = {}
    run_user_checks(c, state)
    run_post_checks(c, state)
    run_search_checks(c, state)
    run_delete_checks(c, state)
    run_pagination_checks(c, state)
    run_field_shape_checks(c, state)

    # Silver
    run_patch_user_checks(c, state)
    run_patch_post_checks(c, state)
    run_filter_by_username_checks(c, state)

    # Gold
    run_reaction_checks(c, state)

    print()
    print(f"{PASSED} passed, {FAILED} failed")
    return 0 if FAILED == 0 else 1


# ---------------------------------------------------------------------------
# Bronze (shipped)
# ---------------------------------------------------------------------------


def run_user_checks(c: httpx.Client, state: dict) -> None:
    r = c.post("/users", json={"username": ALICE})
    check("POST /users creates a user (201)", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        check(
            "POST /users response has the expected user shape",
            set(body.keys()) == USER_KEYS and body["username"] == ALICE,
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
            "POST /posts response has the expected post shape",
            set(body.keys()) == POST_KEYS,
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
# Bronze TODO #1: DELETE checks
# ---------------------------------------------------------------------------


def run_delete_checks(c: httpx.Client, state: dict) -> None:
    # Create a throwaway post so we do not disturb alice_post_id, which is
    # reused by later checks.
    r = c.post(
        "/posts",
        json={"message": f"delete-me-{RUN}"},
        headers={"X-Username": ALICE},
    )
    check("setup: create post to delete (201)", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code != 201:
        return
    pid = r.json()["id"]

    r = c.delete(f"/posts/{pid}")
    check(f"DELETE /posts/{pid} returns 204", r.status_code == 204, detail=f"got {r.status_code}")

    r = c.get(f"/posts/{pid}")
    check(f"GET /posts/{pid} after delete returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    r = c.delete("/posts/99999999")
    check("DELETE /posts/99999999 (missing) returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # Extra assertion beyond the spec: a second DELETE of the same id must
    # also 404, not 204. This guards against an implementation that returns
    # 204 for any id regardless of whether a row was actually removed.
    r = c.delete(f"/posts/{pid}")
    check(
        f"DELETE /posts/{pid} a second time returns 404 (idempotent-but-not-pretending)",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )


# ---------------------------------------------------------------------------
# Bronze TODO #2: pagination checks
# ---------------------------------------------------------------------------


def run_pagination_checks(c: httpx.Client, state: dict) -> None:
    # Create enough posts that limit/offset slicing is actually meaningful.
    for i in range(5):
        c.post(
            "/posts",
            json={"message": f"pag-post-{RUN}-{i}"},
            headers={"X-Username": ALICE},
        )

    r = c.get("/posts", params={"limit": 3})
    check("GET /posts?limit=3 returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        check(
            "GET /posts?limit=3 returns at most 3 items",
            len(r.json()) <= 3,
            detail=f"got {len(r.json())}",
        )

    # offset skips the first K items relative to the unsliced list. Use
    # matching window sizes so the two slices have the same length and the
    # comparison is meaningful regardless of how full the database is.
    r_all = c.get("/posts", params={"limit": 10})
    r_off = c.get("/posts", params={"limit": 8, "offset": 2})
    if r_all.status_code == 200 and r_off.status_code == 200:
        ids_all = [p["id"] for p in r_all.json()]
        ids_off = [p["id"] for p in r_off.json()]
        check(
            "GET /posts?offset=2 skips the first 2 items of the unsliced list",
            ids_off == ids_all[2:10],
            detail=f"all={ids_all} off={ids_off}",
        )

    r = c.get("/posts", params={"limit": 0})
    check("GET /posts?limit=0 returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.get("/posts", params={"limit": 500})
    check("GET /posts?limit=500 returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.get("/posts", params={"offset": -1})
    check("GET /posts?offset=-1 returns 422", r.status_code == 422, detail=f"got {r.status_code}")


# ---------------------------------------------------------------------------
# Bronze TODO #3: exact field-shape checks
# ---------------------------------------------------------------------------


def run_field_shape_checks(c: httpx.Client, state: dict) -> None:
    # Fresh user + post in isolation, so this check does not accidentally
    # pass against stale state from earlier sections.
    uname = f"shape_{RUN}"
    c.post("/users", json={"username": uname})
    post_resp = c.post(
        "/posts",
        json={"message": "shape check"},
        headers={"X-Username": uname},
    )
    post_body = post_resp.json()
    shape_post_id = post_body["id"]

    # --- User shape ---
    r = c.get(f"/users/{uname}")
    check(
        "GET /users/{u} has exactly the documented user shape",
        set(r.json().keys()) == USER_KEYS,
        detail=str(r.json()),
    )

    r = c.get("/users")
    users = r.json()
    match = next((u for u in users if u["username"] == uname), None)
    check(
        "GET /users items have exactly the documented user shape",
        match is not None and set(match.keys()) == USER_KEYS,
        detail=str(match),
    )

    check(
        "POST /users response has exactly the documented user shape",
        # re-create check: the body from our original POST is worth asserting too
        set(c.post("/users", json={"username": f"shape2_{RUN}"}).json().keys()) == USER_KEYS,
    )

    # --- Post shape ---
    check(
        "POST /posts response has exactly the documented post shape",
        set(post_body.keys()) == POST_KEYS,
        detail=str(post_body),
    )

    r = c.get(f"/posts/{shape_post_id}")
    check(
        "GET /posts/{id} has exactly the documented post shape",
        set(r.json().keys()) == POST_KEYS,
        detail=str(r.json()),
    )

    r = c.get("/posts", params={"username": uname})
    items = r.json()
    check(
        "GET /posts items have exactly the documented post shape",
        len(items) >= 1 and all(set(p.keys()) == POST_KEYS for p in items),
        detail=str(items[:1]),
    )


# ---------------------------------------------------------------------------
# Silver: PATCH /users/{username}
# ---------------------------------------------------------------------------


def run_patch_user_checks(c: httpx.Client, state: dict) -> None:
    r = c.patch(f"/users/{ALICE}", json={"bio": "wolf in dog suit"})
    check("PATCH /users/{u} returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        check(
            "PATCH /users/{u} response has the full user shape and updated bio",
            set(r.json().keys()) == USER_KEYS and r.json()["bio"] == "wolf in dog suit",
            detail=str(r.json()),
        )

    # Subsequent GET reflects the change.
    r = c.get(f"/users/{ALICE}")
    check(
        "GET /users/{u} reflects the patched bio",
        r.status_code == 200 and r.json().get("bio") == "wolf in dog suit",
        detail=str(r.json()),
    )

    r = c.patch(f"/users/{GHOST}", json={"bio": "nope"})
    check("PATCH /users/{ghost} returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    r = c.patch(f"/users/{ALICE}", json={"bio": "x" * 201})
    check("PATCH /users oversize bio returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # PATCH with empty body leaves bio alone (partial-update semantics).
    r = c.patch(f"/users/{ALICE}", json={})
    check(
        "PATCH /users with empty body returns 200 and leaves bio unchanged",
        r.status_code == 200 and r.json().get("bio") == "wolf in dog suit",
        detail=str(r.json()),
    )


# ---------------------------------------------------------------------------
# Silver: PATCH /posts/{id} (ownership policy = X-Username must match author)
# ---------------------------------------------------------------------------


def run_patch_post_checks(c: httpx.Client, state: dict) -> None:
    pid = state.get("alice_post_id")
    if pid is None:
        check("PATCH /posts precondition: have an alice post", False, detail="no alice_post_id in state")
        return

    r = c.patch(f"/posts/{pid}", json={"message": "edited by alice"}, headers={"X-Username": ALICE})
    check("PATCH /posts/{id} as author returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        body = r.json()
        check(
            "PATCH /posts/{id} response has the expected post shape",
            set(body.keys()) == POST_KEYS,
            detail=str(body),
        )
        check(
            "PATCH /posts/{id} sets updated_at (non-null)",
            body.get("updated_at") is not None,
            detail=str(body),
        )
        check(
            "PATCH /posts/{id} actually changes message",
            body.get("message") == "edited by alice",
            detail=str(body),
        )

    # Ownership policy: bob cannot edit alice's post.
    r = c.patch(f"/posts/{pid}", json={"message": "hijacked"}, headers={"X-Username": BOB})
    check(
        "PATCH /posts/{id} by non-author returns 403",
        r.status_code == 403,
        detail=f"got {r.status_code}",
    )

    # Still alice's message, not bob's attempted hijack.
    r = c.get(f"/posts/{pid}")
    check(
        "non-author PATCH did not mutate the post",
        r.status_code == 200 and r.json().get("message") == "edited by alice",
        detail=str(r.json()),
    )

    r = c.patch(f"/posts/{pid}", json={"message": "noauth"})
    check("PATCH /posts/{id} missing X-Username returns 400", r.status_code == 400, detail=f"got {r.status_code}")

    r = c.patch("/posts/99999999", json={"message": "x"}, headers={"X-Username": ALICE})
    check("PATCH /posts/99999999 returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    r = c.patch(f"/posts/{pid}", json={"message": "x" * 501}, headers={"X-Username": ALICE})
    check("PATCH /posts/{id} oversize message returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.patch(f"/posts/{pid}", json={"message": ""}, headers={"X-Username": ALICE})
    check("PATCH /posts/{id} empty message returns 422", r.status_code == 422, detail=f"got {r.status_code}")


# ---------------------------------------------------------------------------
# Silver: GET /posts?username=... (compose with ?q= and pagination)
# ---------------------------------------------------------------------------


def run_filter_by_username_checks(c: httpx.Client, state: dict) -> None:
    # CAROL is fresh; she has exactly 2 posts, one with a needle.
    c.post("/users", json={"username": CAROL})
    carol_needle = f"carol_needle_{RUN}"
    c.post("/posts", json={"message": f"carol {carol_needle} post"}, headers={"X-Username": CAROL})
    c.post("/posts", json={"message": "carol boring post"}, headers={"X-Username": CAROL})

    r = c.get("/posts", params={"username": CAROL})
    check(f"GET /posts?username={CAROL} returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        items = r.json()
        check(
            f"GET /posts?username={CAROL} returns only carol's posts",
            len(items) == 2 and all(p["username"] == CAROL for p in items),
            detail=str(items),
        )

    r = c.get("/posts", params={"username": CAROL, "q": carol_needle})
    if r.status_code == 200:
        items = r.json()
        check(
            "GET /posts?username=&q= composes author filter with search",
            len(items) == 1 and carol_needle in items[0]["message"],
            detail=str(items),
        )

    r = c.get("/posts", params={"username": CAROL, "limit": 1})
    if r.status_code == 200:
        check(
            "GET /posts?username=&limit= composes author filter with pagination",
            len(r.json()) == 1,
            detail=str(r.json()),
        )

    # Invalid username format on the query param is a 422, same rule as the body.
    r = c.get("/posts", params={"username": "!!"})
    check(
        "GET /posts?username=!! returns 422 (regex mismatch)",
        r.status_code == 422,
        detail=f"got {r.status_code}",
    )


# ---------------------------------------------------------------------------
# Gold: reactions
# ---------------------------------------------------------------------------


def run_reaction_checks(c: httpx.Client, state: dict) -> None:
    pid = state.get("alice_post_id")
    if pid is None:
        check("reactions precondition: have an alice post", False, detail="no alice_post_id in state")
        return

    r = c.post(f"/posts/{pid}/reactions", json={"username": BOB, "kind": "+1"})
    check("POST /posts/{id}/reactions returns 201", r.status_code == 201, detail=f"got {r.status_code}")
    if r.status_code == 201:
        body = r.json()
        check(
            "reaction response has {post_id, username, kind, created_at}",
            set(body.keys()) == {"post_id", "username", "kind", "created_at"},
            detail=str(body),
        )

    # Same user + same kind on the same post = duplicate -> 409
    r = c.post(f"/posts/{pid}/reactions", json={"username": BOB, "kind": "+1"})
    check(
        "POST duplicate reaction (same user+kind) returns 409",
        r.status_code == 409,
        detail=f"got {r.status_code}",
    )

    # Same user, different kind: allowed (separate row).
    r = c.post(f"/posts/{pid}/reactions", json={"username": BOB, "kind": "heart"})
    check(
        "POST second kind from same user returns 201",
        r.status_code == 201,
        detail=f"got {r.status_code}",
    )

    # Another user's reaction.
    r = c.post(f"/posts/{pid}/reactions", json={"username": ALICE, "kind": "+1"})
    check(
        "POST reaction by another user returns 201",
        r.status_code == 201,
        detail=f"got {r.status_code}",
    )

    # The parent post's .reactions dict reflects the aggregate counts.
    r = c.get(f"/posts/{pid}")
    reactions = r.json().get("reactions", {})
    check(
        "post.reactions aggregates by kind",
        reactions.get("+1") == 2 and reactions.get("heart") == 1,
        detail=str(reactions),
    )

    # Listing endpoint is a flat array, one row per reaction.
    r = c.get(f"/posts/{pid}/reactions")
    check(f"GET /posts/{pid}/reactions returns 200", r.status_code == 200, detail=f"got {r.status_code}")
    if r.status_code == 200:
        items = r.json()
        check(
            "GET /posts/{id}/reactions returns 3 reaction rows with the right shape",
            len(items) == 3
            and all(set(i.keys()) == {"username", "kind", "created_at"} for i in items),
            detail=str(items),
        )

    # 404s: unknown post, unknown user on an existing post.
    r = c.post("/posts/99999999/reactions", json={"username": BOB, "kind": "+1"})
    check("POST reaction on missing post returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    r = c.post(f"/posts/{pid}/reactions", json={"username": GHOST, "kind": "+1"})
    check("POST reaction with unknown user returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    # Validation: empty kind, bad username.
    r = c.post(f"/posts/{pid}/reactions", json={"username": BOB, "kind": ""})
    check("POST reaction with empty kind returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    r = c.post(f"/posts/{pid}/reactions", json={"username": "has spaces", "kind": "+1"})
    check("POST reaction with bad username returns 422", r.status_code == 422, detail=f"got {r.status_code}")

    # DELETE removes all of bob's reactions on this post (both +1 and heart).
    r = c.delete(f"/posts/{pid}/reactions/{BOB}")
    check(
        f"DELETE /posts/{pid}/reactions/{BOB} returns 204",
        r.status_code == 204,
        detail=f"got {r.status_code}",
    )

    r = c.get(f"/posts/{pid}")
    reactions = r.json().get("reactions", {})
    check(
        "after DELETE, bob's reactions are gone and alice's +1 remains",
        reactions.get("+1") == 1 and "heart" not in reactions,
        detail=str(reactions),
    )

    # Second DELETE for the same user now has nothing to delete -> 404.
    r = c.delete(f"/posts/{pid}/reactions/{BOB}")
    check(
        "DELETE reactions a second time returns 404 (nothing left to delete)",
        r.status_code == 404,
        detail=f"got {r.status_code}",
    )

    r = c.delete(f"/posts/99999999/reactions/{BOB}")
    check("DELETE reactions on missing post returns 404", r.status_code == 404, detail=f"got {r.status_code}")

    r = c.delete(f"/posts/{pid}/reactions/{GHOST}")
    check("DELETE reactions for unknown user returns 404", r.status_code == 404, detail=f"got {r.status_code}")


if __name__ == "__main__":
    sys.exit(main())
