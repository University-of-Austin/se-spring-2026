from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from constants import REACTION_KINDS
from dependencies import require_user
from models import ReactionsResponse
from repositories import users as users_repo
from services import reactions as reactions_service

router = APIRouter(tags=["reactions"])


# Built from constants.REACTION_KINDS so adding a new kind in one place
# flows through to this path-param allowlist. Unknown values → 422 via
# FastAPI's enum validation.
ReactionKind = Enum(
    "ReactionKind", {kind: kind for kind in REACTION_KINDS}, type=str,
)


@router.put("/posts/{post_id}/reactions/{kind}")
def add_reaction(
    post_id: int,
    kind: ReactionKind,
    user_id: int = Depends(require_user),
):
    """PUT is idempotent: 201 on create, 204 if the caller already had this
    reaction. No body either way — the resource state is implicit in the URL."""
    created = reactions_service.add_reaction(user_id, post_id, kind.value)
    return Response(
        status_code=status.HTTP_201_CREATED if created else status.HTTP_204_NO_CONTENT
    )


@router.delete("/posts/{post_id}/reactions/{kind}", status_code=status.HTTP_204_NO_CONTENT)
def remove_reaction(
    post_id: int,
    kind: ReactionKind,
    user_id: int = Depends(require_user),
):
    reactions_service.remove_reaction(user_id, post_id, kind.value)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/posts/{post_id}/reactions", response_model=ReactionsResponse)
def get_reactions(
    post_id: int,
    x_username: Optional[str] = Header(default=None),
):
    """Counts are public. If X-Username is supplied and resolves to a known
    user, the response also lists that viewer's own reactions for the post —
    so a client can render "you reacted" badges without a second request.
    Unknown X-Username is rejected (404) to stay consistent with the rest of
    the API's identity semantics."""
    viewer_id: Optional[int] = None
    if x_username is not None:
        viewer = users_repo.get_by_username(x_username)
        if viewer is None:
            raise HTTPException(status_code=404, detail="User not found")
        viewer_id = viewer["id"]
    return reactions_service.get_reactions(post_id, viewer_id)
