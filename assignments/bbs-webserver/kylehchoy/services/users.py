from typing import Optional

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from repositories import users as users_repo


def create_user(username: str) -> dict:
    try:
        return users_repo.create(username)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Username already exists")


def get_user_or_404(username: str) -> dict:
    user = users_repo.get_by_username(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def list_users(limit: int = 50, offset: int = 0) -> list[dict]:
    return users_repo.list_all(limit=limit, offset=offset)


def update_bio(username: str, bio: Optional[str]) -> dict:
    updated = users_repo.update_bio(username, bio)
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    return updated
