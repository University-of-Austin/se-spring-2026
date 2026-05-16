"""COLLATE NOCASE is enforced at the SQL layer. These tests pin that contract.

If the schema loses COLLATE NOCASE the service layer would silently start
distinguishing Alice from alice. verify_api.py catches the 409 case; these
pin the other consequences (lookup, exists_by_username, preserved casing).
"""
import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from repositories import users as users_repo


def test_unique_is_case_insensitive():
    users_repo.create("alice")
    with pytest.raises(IntegrityError):
        users_repo.create("ALICE")


def test_get_by_username_is_case_insensitive():
    users_repo.create("alice")
    assert users_repo.get_by_username("ALICE")["username"] == "alice"
    assert users_repo.get_by_username("Alice")["username"] == "alice"


def test_exists_by_username_is_case_insensitive():
    users_repo.create("alice")
    assert users_repo.exists_by_username("alice")
    assert users_repo.exists_by_username("ALICE")
    assert users_repo.exists_by_username("aLiCe")
    assert not users_repo.exists_by_username("bob")


def test_casing_is_preserved_on_create():
    user = users_repo.create("Alice")
    assert user["username"] == "Alice"
    # Lookup with different casing still finds it and preserves stored form.
    assert users_repo.get_by_username("alice")["username"] == "Alice"


def test_update_bio_via_mixed_case_username():
    users_repo.create("alice")
    updated = users_repo.update_bio("ALICE", "hi")
    assert updated is not None
    assert updated["username"] == "alice"
    assert updated["bio"] == "hi"


def test_update_bio_missing_user_returns_none():
    # Guard for the service-layer 404 path — tested again in test_race_conditions.
    assert users_repo.update_bio("ghost", "hi") is None
    # And confirm it raises HTTPException through the service.
    from services import users as users_service
    with pytest.raises(HTTPException) as exc:
        users_service.update_bio("ghost", "hi")
    assert exc.value.status_code == 404
