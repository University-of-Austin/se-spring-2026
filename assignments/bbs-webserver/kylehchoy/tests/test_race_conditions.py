"""The `if updated is None:` branches in service code are unreachable by HTTP
clients under normal conditions — a concurrent delete between the ownership
check and the UPDATE is what triggers them. Simulate by deleting the row
directly at the repo layer between the service-level check and the write.
"""
import pytest
from fastapi import HTTPException

from repositories import posts as posts_repo
from repositories import users as users_repo
from services import posts as posts_service


def test_edit_post_404_when_row_vanishes():
    """edit_post hits the `updated is None` branch when the post is deleted
    between the service's ownership check and the repo UPDATE."""
    alice = users_repo.create("alice")
    post = posts_repo.create(alice["id"], "original")

    # Monkey-free simulation: delete at the repo layer, then call the service
    # with the now-stale post_id. The service's get_post_or_404 runs first
    # and will raise 404 cleanly — which is the outer branch. To hit the
    # inner `updated is None` path we need the row to exist during the
    # ownership check and vanish before the UPDATE. Patch update_message
    # to delete-then-update.
    original_update = posts_repo.update_message

    def delete_then_update(post_id, message):
        posts_repo.delete(post_id)
        return original_update(post_id, message)

    posts_repo.update_message = delete_then_update
    try:
        with pytest.raises(HTTPException) as exc:
            posts_service.edit_post(post["id"], "new msg", alice["id"])
        assert exc.value.status_code == 404
    finally:
        posts_repo.update_message = original_update


def test_edit_post_outer_404_when_post_missing():
    alice = users_repo.create("alice")
    with pytest.raises(HTTPException) as exc:
        posts_service.edit_post(999, "x", alice["id"])
    assert exc.value.status_code == 404


def test_edit_post_403_when_not_author():
    alice = users_repo.create("alice")
    bob = users_repo.create("bob")
    post = posts_repo.create(alice["id"], "alice's post")
    with pytest.raises(HTTPException) as exc:
        posts_service.edit_post(post["id"], "bob trying to edit", bob["id"])
    assert exc.value.status_code == 403


def test_delete_post_403_when_not_author():
    alice = users_repo.create("alice")
    bob = users_repo.create("bob")
    post = posts_repo.create(alice["id"], "alice's post")
    with pytest.raises(HTTPException) as exc:
        posts_service.delete_post(post["id"], bob["id"])
    assert exc.value.status_code == 403
    # And the post is still there.
    assert posts_repo.get_by_id(post["id"]) is not None


def test_delete_post_404_when_missing():
    alice = users_repo.create("alice")
    with pytest.raises(HTTPException) as exc:
        posts_service.delete_post(999, alice["id"])
    assert exc.value.status_code == 404


def test_add_reaction_404_when_post_vanishes_between_check_and_insert():
    """reactions_repo.add used to swallow FK-violation IntegrityError as a
    duplicate, returning 204 for a post that no longer exists. Simulate the
    race by deleting the post inside a patched add."""
    from repositories import reactions as reactions_repo
    from services import reactions as reactions_service

    alice = users_repo.create("alice")
    post = posts_repo.create(alice["id"], "hello")

    original_add = reactions_repo.add

    def delete_then_add(user_id, post_id, kind):
        posts_repo.delete(post_id)
        return original_add(user_id, post_id, kind)

    reactions_repo.add = delete_then_add
    try:
        with pytest.raises(HTTPException) as exc:
            reactions_service.add_reaction(alice["id"], post["id"], "like")
        assert exc.value.status_code == 404
    finally:
        reactions_repo.add = original_add


def test_add_reaction_duplicate_still_returns_false():
    """Guard against the disambiguation logic breaking the legitimate
    duplicate path — PUT idempotency means the second call returns False."""
    from repositories import reactions as reactions_repo

    alice = users_repo.create("alice")
    post = posts_repo.create(alice["id"], "hello")
    assert reactions_repo.add(alice["id"], post["id"], "like") is True
    assert reactions_repo.add(alice["id"], post["id"], "like") is False


def test_create_reply_404_when_parent_vanishes_between_check_and_insert():
    """create_post used to let the FK IntegrityError escape as a 500 when the
    parent was deleted between _validate_parent and the repo INSERT. Patch
    posts_repo.create to delete the parent first, then call the real insert —
    the FK fails and the service must translate it to a clean 404.

    We create a second unrelated post after `parent` so SQLite's next rowid
    is max+1 and the new reply row does not accidentally reuse the deleted
    parent's id (which would make the FK self-satisfy).
    """
    alice = users_repo.create("alice")
    parent = posts_repo.create(alice["id"], "parent")
    posts_repo.create(alice["id"], "unrelated")  # bumps max(rowid) past parent.id

    original_create = posts_repo.create

    def delete_parent_then_create(user_id, message, parent_id=None):
        if parent_id is not None:
            posts_repo.delete(parent_id)
        return original_create(user_id, message, parent_id=parent_id)

    posts_repo.create = delete_parent_then_create
    try:
        with pytest.raises(HTTPException) as exc:
            posts_service.create_post(alice["id"], "reply", parent_id=parent["id"])
        assert exc.value.status_code == 404
    finally:
        posts_repo.create = original_create
