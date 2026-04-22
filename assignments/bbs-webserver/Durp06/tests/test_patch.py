"""Silver tests: PATCH /users/{username} + PATCH /posts/{id} + silver user shape."""
import pytest


class TestSilverUserShape:
    def test_post_users_returns_bio_and_post_count(self, client):
        r = client.post("/users", json={"username": "alice"})
        assert r.status_code == 201
        body = r.json()
        assert "bio" in body
        assert body["bio"] == ""
        assert "post_count" in body
        assert body["post_count"] == 0

    def test_post_users_with_bio(self, client):
        r = client.post("/users", json={"username": "alice", "bio": "hi there"})
        assert r.status_code == 201
        assert r.json()["bio"] == "hi there"

    def test_post_count_increments(self, client):
        client.post("/users", json={"username": "alice"})
        client.post("/posts", json={"message": "post 1"}, headers={"X-Username": "alice"})
        client.post("/posts", json={"message": "post 2"}, headers={"X-Username": "alice"})
        r = client.get("/users/alice")
        assert r.status_code == 200
        assert r.json()["post_count"] == 2

    def test_patch_users_200(self, client):
        client.post("/users", json={"username": "alice"})
        r = client.patch("/users/alice", json={"bio": "new bio"})
        assert r.status_code == 200
        assert r.json()["bio"] == "new bio"

    def test_patch_users_not_found_404(self, client):
        r = client.patch("/users/nobody", json={"bio": "x"})
        assert r.status_code == 404

    def test_patch_users_bio_too_long_422(self, client):
        client.post("/users", json={"username": "alice"})
        r = client.patch("/users/alice", json={"bio": "x" * 201})
        assert r.status_code == 422


class TestSilverPostUpdatedAt:
    def test_post_posts_includes_updated_at(self, client):
        client.post("/users", json={"username": "alice"})
        r = client.post("/posts", json={"message": "hello"}, headers={"X-Username": "alice"})
        assert r.status_code == 201
        body = r.json()
        assert "updated_at" in body
        assert body["updated_at"] == body["created_at"]

    def test_get_posts_by_id_includes_updated_at(self, client):
        client.post("/users", json={"username": "alice"})
        r = client.post("/posts", json={"message": "hello"}, headers={"X-Username": "alice"})
        post_id = r.json()["id"]
        r = client.get(f"/posts/{post_id}")
        assert r.status_code == 200
        assert "updated_at" in r.json()

    def test_get_posts_list_includes_updated_at(self, client):
        client.post("/users", json={"username": "alice"})
        client.post("/posts", json={"message": "hello"}, headers={"X-Username": "alice"})
        r = client.get("/posts")
        assert r.status_code == 200
        posts = r.json()
        assert len(posts) >= 1
        assert "updated_at" in posts[0]


class TestPatchPosts:
    def test_patch_posts_200(self, client):
        client.post("/users", json={"username": "alice"})
        r = client.post("/posts", json={"message": "original"}, headers={"X-Username": "alice"})
        post_id = r.json()["id"]
        created_at = r.json()["created_at"]
        r = client.patch(f"/posts/{post_id}", json={"message": "patched"}, headers={"X-Username": "alice"})
        assert r.status_code == 200
        body = r.json()
        assert body["message"] == "patched"
        assert body["updated_at"] >= created_at

    def test_patch_posts_no_header_400(self, client):
        client.post("/users", json={"username": "alice"})
        r = client.post("/posts", json={"message": "original"}, headers={"X-Username": "alice"})
        post_id = r.json()["id"]
        r = client.patch(f"/posts/{post_id}", json={"message": "patched"})
        assert r.status_code == 400

    def test_patch_posts_wrong_user_403(self, client):
        client.post("/users", json={"username": "alice"})
        client.post("/users", json={"username": "bob"})
        r = client.post("/posts", json={"message": "original"}, headers={"X-Username": "alice"})
        post_id = r.json()["id"]
        r = client.patch(f"/posts/{post_id}", json={"message": "hijack"}, headers={"X-Username": "bob"})
        assert r.status_code == 403

    def test_patch_posts_not_found_404(self, client):
        client.post("/users", json={"username": "alice"})
        r = client.patch("/posts/99999999", json={"message": "ghost"}, headers={"X-Username": "alice"})
        assert r.status_code == 404

    def test_patch_posts_empty_message_422(self, client):
        client.post("/users", json={"username": "alice"})
        r = client.post("/posts", json={"message": "original"}, headers={"X-Username": "alice"})
        post_id = r.json()["id"]
        r = client.patch(f"/posts/{post_id}", json={"message": ""}, headers={"X-Username": "alice"})
        assert r.status_code == 422
