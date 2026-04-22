"""Gold tests: cursor-based pagination on GET /posts."""
import base64
import json
import pytest


def encode_cursor(last_id: int) -> str:
    return base64.urlsafe_b64encode(json.dumps({"id": last_id}).encode()).decode()


def _seed_posts(client, username, count):
    client.post("/users", json={"username": username})
    ids = []
    for i in range(count):
        r = client.post("/posts", json={"message": f"cursor post {i}"}, headers={"X-Username": username})
        assert r.status_code == 201
        ids.append(r.json()["id"])
    return ids


def test_no_cursor_returns_bare_array(client):
    _seed_posts(client, "alice", 7)
    r = client.get("/posts")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list), f"Expected list, got {type(body)}"
    assert len(body) == 7


def test_cursor_returns_envelope(client):
    ids = _seed_posts(client, "alice", 7)
    # cursor pointing before first post
    cursor = encode_cursor(ids[0] - 1)
    r = client.get("/posts", params={"cursor": cursor})
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)
    assert "posts" in body
    assert "next_cursor" in body


def test_cursor_pagination_no_gaps_no_dups(client):
    ids = _seed_posts(client, "alice", 7)
    first_id = min(ids)
    cursor = encode_cursor(first_id - 1)
    limit = 3
    accumulated = set()
    current_cursor = cursor
    while current_cursor is not None:
        r = client.get("/posts", params={"cursor": current_cursor, "limit": limit})
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, dict) and "posts" in body
        page_ids = {p["id"] for p in body["posts"]}
        assert len(accumulated & page_ids) == 0, f"Duplicate ids: {accumulated & page_ids}"
        accumulated |= page_ids
        current_cursor = body["next_cursor"]
    assert accumulated == set(ids)


def test_cursor_with_limit(client):
    ids = _seed_posts(client, "alice", 7)
    cursor = encode_cursor(ids[1] - 1)  # start at 2nd post
    r = client.get("/posts", params={"cursor": cursor, "limit": 2})
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)
    assert len(body["posts"]) == 2
    # next_cursor encodes id of last post in page
    assert body["next_cursor"] == encode_cursor(body["posts"][-1]["id"])


def test_final_page_next_cursor_is_null(client):
    ids = _seed_posts(client, "alice", 3)
    cursor = encode_cursor(min(ids) - 1)
    r = client.get("/posts", params={"cursor": cursor, "limit": 10})
    assert r.status_code == 200
    body = r.json()
    # fewer than limit means no more pages
    assert body["next_cursor"] is None


def test_cursor_invalid_base64_422(client):
    r = client.get("/posts", params={"cursor": "not-valid-base64!!!"})
    assert r.status_code == 422


def test_cursor_valid_b64_invalid_json_422(client):
    bad = base64.urlsafe_b64encode(b"not-json").decode()
    r = client.get("/posts", params={"cursor": bad})
    assert r.status_code == 422
