"""GET /posts must return the spec's Gold cursor envelope —
`{"posts": [...], "next_cursor": "..."}` — on every code path.

Regression guard: the earlier shape was a bare JSON array with the cursor
surfaced on an `X-Next-Cursor` response header. A future refactor that
accidentally restores the bare-array shape would pass the per-row field
shape checks in verify_api (POST_KEYS is per-item), so we assert the
envelope keys here at the HTTP boundary.
"""
from repositories import posts as posts_repo
from repositories import users as users_repo


def _envelope(r):
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, dict), f"expected dict envelope, got {type(body).__name__}"
    assert set(body.keys()) >= {"posts", "next_cursor"}, f"keys were {set(body.keys())}"
    assert isinstance(body["posts"], list)
    return body


def test_get_posts_empty_returns_envelope(client):
    body = _envelope(client.get("/posts"))
    assert body["posts"] == []
    assert body["next_cursor"] is None


def test_get_posts_first_page_emits_next_cursor_when_more_exist(client):
    alice = users_repo.create("alice")
    ids = [posts_repo.create(alice["id"], f"post {i}")["id"] for i in range(5)]
    body = _envelope(client.get("/posts", params={"limit": 3}))
    assert len(body["posts"]) == 3
    assert body["next_cursor"] is not None
    # Newest-first: the highest 3 ids.
    assert [p["id"] for p in body["posts"]] == sorted(ids, reverse=True)[:3]


def test_get_posts_cursor_walk_returns_envelope_every_page(client):
    alice = users_repo.create("alice")
    for i in range(7):
        posts_repo.create(alice["id"], f"post {i}")

    seen = []
    cursor = None
    pages = 0
    while pages < 10:
        params = {"limit": 3}
        if cursor is not None:
            params["cursor"] = cursor
        body = _envelope(client.get("/posts", params=params))
        seen.extend(p["id"] for p in body["posts"])
        cursor = body["next_cursor"]
        pages += 1
        if cursor is None:
            break

    assert pages == 3  # ceil(7/3)
    assert len(seen) == 7
    assert len(set(seen)) == 7  # no duplicates


def test_get_posts_last_page_has_null_next_cursor(client):
    alice = users_repo.create("alice")
    posts_repo.create(alice["id"], "only post")
    body = _envelope(client.get("/posts", params={"limit": 10}))
    assert len(body["posts"]) == 1
    assert body["next_cursor"] is None


def test_get_posts_offset_path_also_returns_envelope(client):
    """The offset path — kept for bronze backward compatibility — must also
    honor the envelope shape, with next_cursor=None since offset callers
    paginate by incrementing offset themselves."""
    alice = users_repo.create("alice")
    for i in range(5):
        posts_repo.create(alice["id"], f"post {i}")
    body = _envelope(client.get("/posts", params={"limit": 3, "offset": 1}))
    assert len(body["posts"]) == 3
    assert body["next_cursor"] is None


def test_get_posts_search_path_returns_envelope(client):
    alice = users_repo.create("alice")
    posts_repo.create(alice["id"], "hello world")
    posts_repo.create(alice["id"], "goodbye")
    body = _envelope(client.get("/posts", params={"q": "hello"}))
    assert len(body["posts"]) == 1
    assert body["posts"][0]["message"] == "hello world"
    assert body["next_cursor"] is None


def test_get_posts_cursor_plus_offset_rejected_422(client):
    alice = users_repo.create("alice")
    for i in range(5):
        posts_repo.create(alice["id"], f"post {i}")
    body = _envelope(client.get("/posts", params={"limit": 3}))
    cursor = body["next_cursor"]
    assert cursor is not None
    r = client.get("/posts", params={"limit": 3, "cursor": cursor, "offset": 1})
    assert r.status_code == 422
    assert "cursor and offset cannot be combined" in r.json()["detail"]


def test_get_posts_invalid_cursor_rejected_422(client):
    r = client.get("/posts", params={"cursor": "not-base64!!!"})
    assert r.status_code == 422
    assert r.json()["detail"] == "Invalid cursor"
