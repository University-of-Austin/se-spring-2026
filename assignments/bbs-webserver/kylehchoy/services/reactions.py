from typing import Optional

from fastapi import HTTPException

from constants import REACTION_KINDS
from repositories import posts as posts_repo
from repositories import reactions as reactions_repo


def add_reaction(user_id: int, post_id: int, kind: str) -> bool:
    """True if newly created, False if already existed. Raises 404 if the
    post doesn't exist — either at the initial check or (via PostVanished)
    because it was deleted between the check and the INSERT."""
    if posts_repo.get_by_id(post_id) is None:
        raise HTTPException(status_code=404, detail="Post not found")
    try:
        return reactions_repo.add(user_id, post_id, kind)
    except reactions_repo.PostVanished:
        raise HTTPException(status_code=404, detail="Post not found")


def remove_reaction(user_id: int, post_id: int, kind: str) -> None:
    if posts_repo.get_by_id(post_id) is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if not reactions_repo.remove(user_id, post_id, kind):
        raise HTTPException(status_code=404, detail="Reaction not found")


def get_reactions(post_id: int, viewer_user_id: Optional[int]) -> dict:
    if posts_repo.get_by_id(post_id) is None:
        raise HTTPException(status_code=404, detail="Post not found")
    raw = reactions_repo.counts_for_post(post_id)
    counts = {k: raw.get(k, 0) for k in REACTION_KINDS}
    out: dict = {"counts": counts, "total": sum(counts.values())}
    if viewer_user_id is not None:
        out["user_reactions"] = reactions_repo.user_reactions_for_post(
            viewer_user_id, post_id,
        )
    return out
