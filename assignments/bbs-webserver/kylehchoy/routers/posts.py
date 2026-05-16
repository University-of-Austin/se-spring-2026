from typing import Optional

from fastapi import APIRouter, Depends, Header, Query, Response, status

from dependencies import require_user
from models import PostCreate, PostMessage, PostResponse
from services import posts as posts_service

router = APIRouter(tags=["posts"])


def _etag_for(post: dict) -> str:
    """Weak ETag W/"<id>-<etag_source>". etag_source is COALESCE(updated_at, created_at)
    from the repository SELECT, so it advances whenever the resource is mutated."""
    return f'W/"{post["id"]}-{post["etag_source"]}"'


@router.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    body: PostCreate,
    response: Response,
    user_id: int = Depends(require_user),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    if idempotency_key is not None:
        post = posts_service.create_post_idempotent(
            user_id, idempotency_key, body.message, parent_id=body.parent_id,
        )
    else:
        post = posts_service.create_post(
            user_id, body.message, parent_id=body.parent_id,
        )
    response.headers["Location"] = f"/posts/{post['id']}"
    return post


@router.get("/posts")
def list_posts(
    q: Optional[str] = Query(default=None),
    username: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    cursor: Optional[str] = Query(default=None),
    sort: str = Query(default="recent"),
    window: Optional[int] = Query(default=None, ge=1, le=24 * 365),
):
    """Gold cursor pagination per the assignment spec: response is the
    envelope `{"posts": [...], "next_cursor": "..."}`. `next_cursor` is
    `null` on the last page (and on the offset/search/top paths where
    cursor pagination does not apply). No response_model here — the FTS
    search path adds a per-row `snippet` field that a fixed model would
    strip; the service projects each row to a known keyset before
    returning.
    """
    posts, next_cursor = posts_service.list_posts(
        q=q, username=username, limit=limit, offset=offset, cursor=cursor,
        sort=sort, window_hours=window,
    )
    return {"posts": posts, "next_cursor": next_cursor}


# NOTE: /posts/trending and /posts/{post_id}/replies must be declared before
# /posts/{post_id} — FastAPI matches routes in declaration order, and the int
# path converter on {post_id} would reject "trending" with a 422 before the
# trending handler ever ran.
@router.get("/posts/trending", response_model=list[PostResponse])
def get_trending(
    window: int = Query(default=24, ge=1, le=24 * 365),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Preset shortcut for GET /posts?sort=top&window=<hours>&limit=<n>.
    Exists as its own URL so clients can link to 'what's hot' without
    constructing query params."""
    return posts_service.list_trending(window_hours=window, limit=limit)


@router.get("/posts/{post_id}/replies", response_model=list[PostResponse])
def get_replies(
    post_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return posts_service.list_replies(post_id, limit=limit, offset=offset)


@router.get("/posts/{post_id}", response_model=PostResponse)
def get_post(
    post_id: int,
    response: Response,
    if_none_match: Optional[str] = Header(default=None),
):
    post = posts_service.get_post_or_404(post_id)
    etag = _etag_for(post)
    if if_none_match == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)
    response.headers["ETag"] = etag
    return post


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, user_id: int = Depends(require_user)):
    posts_service.delete_post(post_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/posts/{post_id}", response_model=PostResponse)
def patch_post(
    post_id: int, body: PostMessage, response: Response,
    user_id: int = Depends(require_user),
):
    post = posts_service.edit_post(post_id, body.message, user_id)
    response.headers["ETag"] = _etag_for(post)
    return post
