from typing import Optional

from fastapi import Header, HTTPException

from repositories import users as users_repo


def require_user(x_username: Optional[str] = Header(default=None)) -> int:
    """Identity dependency for authenticated endpoints. Returns the user's
    numeric id.

    Returns just the id — not the public read model — because every caller
    only needs the id to authorize/author. Reaching into `users_repo.get_by_username`
    here would drag `bio`, `created_at`, and a correlated `post_count`
    COUNT(*) subquery into the auth path, which every POST/PATCH/DELETE
    would then pay for on each request.
    """
    if x_username is None:
        raise HTTPException(status_code=400, detail="X-Username header required")
    user_id = users_repo.get_id_by_username(x_username)
    if user_id is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user_id
