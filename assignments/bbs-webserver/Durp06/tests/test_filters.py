"""Bronze tests: ?q=, ?limit=, ?offset=; GET /users/{username}/posts."""
import pytest


def _setup_alice_posts(client, count=5):
    client.post("/users", json={"username": "alice"})
    for i in range(count):
        client.post("/posts", json={"message": f"post {i}"}, headers={"X-Username": "alice"})


def test_limit_caps_results(client):
    _setup_alice_posts(client, 5)
    r = client.get("/posts", params={"limit": 2})
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_offset_skips_rows(client):
    _setup_alice_posts(client, 5)
    r0 = client.get("/posts", params={"limit": 1, "offset": 0})
    r1 = client.get("/posts", params={"limit": 1, "offset": 1})
    assert r0.status_code == 200
    assert r1.status_code == 200
    assert r0.json()[0]["id"] != r1.json()[0]["id"]


def test_limit_zero_422(client):
    r = client.get("/posts", params={"limit": 0})
    assert r.status_code == 422


def test_limit_too_large_422(client):
    r = client.get("/posts", params={"limit": 500})
    assert r.status_code == 422


def test_offset_negative_422(client):
    r = client.get("/posts", params={"offset": -1})
    assert r.status_code == 422


def test_search_returns_matching(client):
    client.post("/users", json={"username": "alice"})
    client.post("/posts", json={"message": "find this needle here"}, headers={"X-Username": "alice"})
    client.post("/posts", json={"message": "nothing to see"}, headers={"X-Username": "alice"})
    r = client.get("/posts", params={"q": "needle"})
    assert r.status_code == 200
    results = r.json()
    assert len(results) >= 1
    assert all("needle" in p["message"] for p in results)


def test_get_user_posts_200(client):
    client.post("/users", json={"username": "alice"})
    client.post("/users", json={"username": "bob"})
    client.post("/posts", json={"message": "alice post"}, headers={"X-Username": "alice"})
    client.post("/posts", json={"message": "bob post"}, headers={"X-Username": "bob"})
    r = client.get("/users/alice/posts")
    assert r.status_code == 200
    posts = r.json()
    assert isinstance(posts, list)
    assert all(p["username"] == "alice" for p in posts)
    assert len(posts) >= 1


def test_get_user_posts_empty_user(client):
    client.post("/users", json={"username": "alice"})
    r = client.get("/users/alice/posts")
    assert r.status_code == 200
    assert r.json() == []


def test_get_user_posts_unknown_user_404(client):
    r = client.get("/users/nobody/posts")
    assert r.status_code == 404


def test_username_filter_on_get_posts(client):
    client.post("/users", json={"username": "alice"})
    client.post("/users", json={"username": "bob"})
    client.post("/posts", json={"message": "alice post"}, headers={"X-Username": "alice"})
    client.post("/posts", json={"message": "bob post"}, headers={"X-Username": "bob"})
    r = client.get("/posts", params={"username": "alice"})
    assert r.status_code == 200
    posts = r.json()
    assert all(p["username"] == "alice" for p in posts)


def test_username_filter_ghost_returns_empty(client):
    r = client.get("/posts", params={"username": "ghost"})
    assert r.status_code == 200
    assert r.json() == []
