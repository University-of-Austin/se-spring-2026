from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

import db


class PostVanished(Exception):
    """Raised by add() when the INSERT fails because the referenced post was
    deleted between the service-layer existence check and the INSERT. The
    service translates this to a 404; the repository refuses to collapse it
    with the legitimate duplicate-reaction case."""


def add(user_id: int, post_id: int, kind: str) -> bool:
    """Returns True if a new reaction was inserted, False if it already existed
    (PUT is idempotent — "ensure this reaction exists").

    Raises PostVanished if the INSERT fails because the post no longer exists.
    Two INSERT failure modes share IntegrityError — the duplicate (PK) path
    and the FK path — so we disambiguate by reading back: if the reaction row
    now exists for (user_id, post_id, kind), it was a duplicate; otherwise
    the FK failed and the post is gone.
    """
    try:
        with db.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO reactions (user_id, post_id, kind) "
                    "VALUES (:uid, :pid, :kind)"
                ),
                {"uid": user_id, "pid": post_id, "kind": kind},
            )
        return True
    except IntegrityError:
        with db.engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT 1 FROM reactions "
                    "WHERE user_id = :uid AND post_id = :pid AND kind = :kind"
                ),
                {"uid": user_id, "pid": post_id, "kind": kind},
            ).fetchone()
        if row is not None:
            return False
        raise PostVanished


def remove(user_id: int, post_id: int, kind: str) -> bool:
    with db.engine.begin() as conn:
        result = conn.execute(
            text(
                "DELETE FROM reactions "
                "WHERE user_id = :uid AND post_id = :pid AND kind = :kind"
            ),
            {"uid": user_id, "pid": post_id, "kind": kind},
        )
    return result.rowcount > 0


def counts_for_post(post_id: int) -> dict[str, int]:
    with db.engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT kind, COUNT(*) AS n FROM reactions "
                "WHERE post_id = :pid GROUP BY kind"
            ),
            {"pid": post_id},
        ).fetchall()
    return {r.kind: r.n for r in rows}


def user_reactions_for_post(user_id: int, post_id: int) -> list[str]:
    with db.engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT kind FROM reactions "
                "WHERE user_id = :uid AND post_id = :pid ORDER BY kind"
            ),
            {"uid": user_id, "pid": post_id},
        ).fetchall()
    return [r.kind for r in rows]
