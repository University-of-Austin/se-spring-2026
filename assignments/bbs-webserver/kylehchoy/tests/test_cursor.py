"""Cursor encode/decode — verify_api covers the happy path, these cover the error branches."""
import base64
import json

import pytest
from fastapi import HTTPException

from services.posts import _decode_cursor, _encode_cursor


def test_encode_decode_roundtrip():
    assert _decode_cursor(_encode_cursor(42)) == 42


def test_encode_strips_padding():
    # Implementation contract: we strip '=' so cursors are clean query params.
    encoded = _encode_cursor(1)
    assert "=" not in encoded


def test_decode_accepts_unpadded_and_padded():
    raw = json.dumps({"id": 7}).encode("utf-8")
    padded = base64.urlsafe_b64encode(raw).decode("ascii")
    unpadded = padded.rstrip("=")
    assert _decode_cursor(padded) == 7
    assert _decode_cursor(unpadded) == 7


@pytest.mark.parametrize("bad", [
    "",                                  # empty
    "!!!not-base64!!!",                  # malformed base64
    base64.urlsafe_b64encode(b"not json").decode().rstrip("="),  # valid b64, bad json
    base64.urlsafe_b64encode(b'{"wrong": 1}').decode().rstrip("="),  # missing 'id' key
    base64.urlsafe_b64encode(b'{"id": "abc"}').decode().rstrip("="),  # non-int id
    base64.urlsafe_b64encode(b'[1, 2, 3]').decode().rstrip("="),  # not an object
])
def test_decode_rejects_malformed(bad):
    with pytest.raises(HTTPException) as exc:
        _decode_cursor(bad)
    assert exc.value.status_code == 422
    assert exc.value.detail == "Invalid cursor"


def test_cursor_plus_offset_rejected():
    """Cursor and offset are two pagination modes; accepting both would force
    a silent precedence rule. The API rejects the combination with 422
    before touching the DB."""
    from services.posts import list_posts

    valid_cursor = _encode_cursor(100)
    with pytest.raises(HTTPException) as exc:
        list_posts(q=None, username=None, limit=10, offset=5, cursor=valid_cursor)
    assert exc.value.status_code == 422
    assert "cursor and offset cannot be combined" in exc.value.detail


def test_cursor_with_offset_zero_is_allowed():
    """offset=0 is FastAPI's Query default — it means 'not supplied,' so the
    cursor path must still work when offset is at its default value."""
    from repositories import users as users_repo
    from services.posts import list_posts

    users_repo.create("alice")
    # Empty table beyond that user is fine; we're asserting the call doesn't
    # raise when cursor is present with offset at its default.
    posts, _ = list_posts(
        q=None, username=None, limit=10, offset=0, cursor=_encode_cursor(999),
    )
    assert posts == []
