from typing import Optional

from sqlalchemy import text

import db


def get(user_id: int, key: str) -> Optional[dict]:
    """Look up a stored idempotency record. Returns {body_hash, response_json}
    or None. response_json may be '' if the winner claimed the key but has
    not yet written its response — callers distinguish 'in progress' from
    'completed' by checking for the empty string."""
    with db.engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT body_hash, response_json FROM idempotency_keys "
                "WHERE user_id = :uid AND key = :key"
            ),
            {"uid": user_id, "key": key},
        ).fetchone()
    if row is None:
        return None
    return {"body_hash": row.body_hash, "response_json": row.response_json}


def claim(conn, user_id: int, key: str, body_hash: str) -> None:
    """Insert a PENDING idempotency row inside the caller's transaction.

    Raises IntegrityError (via the underlying INSERT) if another transaction
    already claimed this (user_id, key). The caller treats that as the loser
    signal, rolls back, and replays the winner's stored response.
    """
    conn.execute(
        text(
            "INSERT INTO idempotency_keys (user_id, key, body_hash, response_json) "
            "VALUES (:uid, :key, :hash, '')"
        ),
        {"uid": user_id, "key": key, "hash": body_hash},
    )


def finalize(conn, user_id: int, key: str, response_json: str) -> None:
    """Write the final response payload onto a previously claimed row. Must
    run inside the same transaction as claim() so callers who see a
    non-empty response_json are guaranteed to see a completed payload."""
    conn.execute(
        text(
            "UPDATE idempotency_keys SET response_json = :resp "
            "WHERE user_id = :uid AND key = :key"
        ),
        {"resp": response_json, "uid": user_id, "key": key},
    )
