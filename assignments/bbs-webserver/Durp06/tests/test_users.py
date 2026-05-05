"""Bronze tests: POST/GET /users, GET /users/{username}."""
import pytest


def test_post_users_creates_user(client):
    r = client.post("/users", json={"username": "alice"})
    assert r.status_code == 201
    body = r.json()
    assert "username" in body
    assert body["username"] == "alice"
    assert "created_at" in body


def test_post_users_duplicate_409(client):
    client.post("/users", json={"username": "alice"})
    r = client.post("/users", json={"username": "alice"})
    assert r.status_code == 409


def test_post_users_too_short_422(client):
    r = client.post("/users", json={"username": "ab"})
    assert r.status_code == 422


def test_post_users_too_long_422(client):
    r = client.post("/users", json={"username": "a" * 21})
    assert r.status_code == 422


def test_post_users_bad_regex_422(client):
    r = client.post("/users", json={"username": "has spaces"})
    assert r.status_code == 422


def test_post_users_missing_body_422(client):
    r = client.post("/users", json={})
    assert r.status_code == 422


def test_get_users_returns_200_bare_array(client):
    client.post("/users", json={"username": "alice"})
    client.post("/users", json={"username": "bob"})
    r = client.get("/users")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    usernames = [u["username"] for u in body]
    assert "alice" in usernames
    assert "bob" in usernames


def test_get_user_by_username_200(client):
    client.post("/users", json={"username": "alice"})
    r = client.get("/users/alice")
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "alice"


def test_get_user_by_username_404(client):
    r = client.get("/users/nobody")
    assert r.status_code == 404
