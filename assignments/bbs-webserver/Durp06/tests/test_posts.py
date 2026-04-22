"""Bronze tests: POST /posts, GET /posts, GET /posts/{id}, DELETE /posts/{id}."""
import pytest


def test_post_posts_creates_post(client):
    client.post("/users", json={"username": "alice"})
    r = client.post("/posts", json={"message": "hello world"}, headers={"X-Username": "alice"})
    assert r.status_code == 201
    body = r.json()
    assert "id" in body
    assert body["username"] == "alice"
    assert body["message"] == "hello world"
    assert "created_at" in body


def test_post_posts_without_header_400(client):
    r = client.post("/posts", json={"message": "hi"})
    assert r.status_code == 400


def test_post_posts_unknown_user_404(client):
    r = client.post("/posts", json={"message": "hi"}, headers={"X-Username": "nobody"})
    assert r.status_code == 404


def test_post_posts_empty_message_422(client):
    client.post("/users", json={"username": "alice"})
    r = client.post("/posts", json={"message": ""}, headers={"X-Username": "alice"})
    assert r.status_code == 422


def test_post_posts_too_long_message_422(client):
    client.post("/users", json={"username": "alice"})
    r = client.post("/posts", json={"message": "x" * 501}, headers={"X-Username": "alice"})
    assert r.status_code == 422


def test_get_posts_returns_bare_array(client):
    client.post("/users", json={"username": "alice"})
    client.post("/posts", json={"message": "hello"}, headers={"X-Username": "alice"})
    r = client.get("/posts")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)


def test_get_posts_by_id_200(client):
    client.post("/users", json={"username": "alice"})
    r = client.post("/posts", json={"message": "hello"}, headers={"X-Username": "alice"})
    post_id = r.json()["id"]
    r = client.get(f"/posts/{post_id}")
    assert r.status_code == 200
    assert r.json()["id"] == post_id


def test_get_posts_by_id_404(client):
    r = client.get("/posts/99999999")
    assert r.status_code == 404


def test_delete_post_204(client):
    client.post("/users", json={"username": "alice"})
    r = client.post("/posts", json={"message": "to delete"}, headers={"X-Username": "alice"})
    post_id = r.json()["id"]
    r = client.delete(f"/posts/{post_id}")
    assert r.status_code == 204


def test_delete_post_then_get_404(client):
    client.post("/users", json={"username": "alice"})
    r = client.post("/posts", json={"message": "to delete"}, headers={"X-Username": "alice"})
    post_id = r.json()["id"]
    client.delete(f"/posts/{post_id}")
    r = client.get(f"/posts/{post_id}")
    assert r.status_code == 404


def test_delete_nonexistent_post_404(client):
    r = client.delete("/posts/99999999")
    assert r.status_code == 404
