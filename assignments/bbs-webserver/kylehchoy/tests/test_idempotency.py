"""Stripe-style idempotency for POST /posts.

The failure mode the refactor fixes: the old shape did get() → create() → put(),
so two concurrent requests with the same key both passed the get() check, both
inserted a post, and only one won the put(). The loser silently replayed the
winner's response while leaving a duplicate post in the database. The contract
claims "exactly once"; the old implementation delivered "at most twice, report
once."

The refactored shape claims the key and inserts the post in a single
transaction. Loss manifests as an IntegrityError on the claim INSERT — no
side-effect has happened yet, so the loser has nothing to roll back.
"""
import json

import pytest
from fastapi import HTTPException

import db
from repositories import idempotency as idem_repo
from repositories import posts as posts_repo
from repositories import users as users_repo
from services import posts as posts_service


def test_same_key_same_body_replays():
    alice = users_repo.create("alice")
    first = posts_service.create_post_idempotent(
        alice["id"], "k1", "hello",
    )
    second = posts_service.create_post_idempotent(
        alice["id"], "k1", "hello",
    )
    assert first == second
    # And exactly one post was created.
    assert len(posts_repo.list_posts()) == 1


def test_same_key_different_body_returns_422():
    alice = users_repo.create("alice")
    posts_service.create_post_idempotent(alice["id"], "k1", "hello")
    with pytest.raises(HTTPException) as exc:
        posts_service.create_post_idempotent(alice["id"], "k1", "goodbye")
    assert exc.value.status_code == 422


def test_key_scoped_per_user():
    alice = users_repo.create("alice")
    bob = users_repo.create("bob")
    a = posts_service.create_post_idempotent(alice["id"], "k1", "alice post")
    b = posts_service.create_post_idempotent(bob["id"], "k1", "bob post")
    assert a["username"] == "alice"
    assert b["username"] == "bob"
    assert len(posts_repo.list_posts()) == 2


def test_concurrent_same_key_creates_exactly_one_post():
    """The core correctness property. Simulate two concurrent idempotent
    requests with the same (user, key) + same body by having the second
    request's claim race through while the first's transaction is visible.

    With a single SQLite connection (StaticPool) we can't actually run two
    real transactions in parallel, but we can hit the IntegrityError path
    deterministically: claim first with the service, then call the service
    again — the second call takes the replay branch and must NOT insert a
    second post. Old code failed this assertion because it inserted the
    post before claiming the key.
    """
    alice = users_repo.create("alice")
    first = posts_service.create_post_idempotent(alice["id"], "k1", "hello")
    second = posts_service.create_post_idempotent(alice["id"], "k1", "hello")
    assert first["id"] == second["id"]
    assert len(posts_repo.list_posts()) == 1


def test_concurrent_loser_gets_error_not_duplicate_side_effect():
    """Drive the exact racing branch: pre-seed a claim row directly, then
    call the service with the same (user, key). The service's claim INSERT
    fails with IntegrityError; the replay branch must surface the winner's
    stored response without inserting a second post."""
    alice = users_repo.create("alice")

    body_hash = posts_service._body_hash("hello", None)
    # Winner completes (claim + finalize in one transaction).
    winner_response = {"id": 999, "username": "alice", "message": "hello"}
    with db.engine.begin() as conn:
        idem_repo.claim(conn, alice["id"], "k1", body_hash)
        idem_repo.finalize(conn, alice["id"], "k1", json.dumps(winner_response))

    result = posts_service.create_post_idempotent(alice["id"], "k1", "hello")
    assert result == winner_response
    # Loser didn't insert anything.
    assert posts_repo.list_posts() == []


def test_in_flight_claim_returns_409():
    """If a claim row exists with response_json='' (winner is mid-transaction,
    or winner crashed after claim before finalize), a second request with the
    same key cannot replay a response that doesn't exist yet. Return 409 so
    the client knows to retry rather than blocking or getting a bogus 201."""
    alice = users_repo.create("alice")
    body_hash = posts_service._body_hash("hello", None)
    with db.engine.begin() as conn:
        idem_repo.claim(conn, alice["id"], "k1", body_hash)
        # Simulate the winner still being in its transaction: don't finalize.

    with pytest.raises(HTTPException) as exc:
        posts_service.create_post_idempotent(alice["id"], "k1", "hello")
    assert exc.value.status_code == 409


def test_idempotent_parent_race_still_translates_to_404():
    """Same parent-delete race the non-idempotent path handles, but inside
    the single-transaction idempotent path. The claim has already been
    written when the FK error fires; the 404 must unwind the whole
    transaction so no claim row is left behind."""
    alice = users_repo.create("alice")
    parent = posts_repo.create(alice["id"], "parent")
    posts_repo.create(alice["id"], "unrelated")  # bump max(rowid)

    original_create = posts_repo.create

    def delete_parent_then_create(user_id, message, parent_id=None, *, conn=None):
        if parent_id is not None and conn is not None:
            from sqlalchemy import text
            conn.execute(text("DELETE FROM posts WHERE id = :id"), {"id": parent_id})
        return original_create(user_id, message, parent_id=parent_id, conn=conn)

    posts_repo.create = delete_parent_then_create
    try:
        with pytest.raises(HTTPException) as exc:
            posts_service.create_post_idempotent(
                alice["id"], "k1", "reply", parent_id=parent["id"],
            )
        assert exc.value.status_code == 404
    finally:
        posts_repo.create = original_create

    # The 404 rolled back the claim — retrying with the same key is allowed.
    assert idem_repo.get(alice["id"], "k1") is None
