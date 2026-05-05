from fastapi import APIRouter, Query, Response, status

from models import PostResponse, UserBioPatch, UserCreate, UserResponse
from services import posts as posts_service
from services import users as users_service

router = APIRouter(tags=["users"])


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, response: Response):
    user = users_service.create_user(body.username)
    response.headers["Location"] = f"/users/{user['username']}"
    return user


@router.get("/users", response_model=list[UserResponse])
def list_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return users_service.list_users(limit=limit, offset=offset)


@router.get("/users/{username}", response_model=UserResponse)
def get_user(username: str):
    return users_service.get_user_or_404(username)


@router.get("/users/{username}/posts", response_model=list[PostResponse])
def get_user_posts(
    username: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return posts_service.list_posts_by_username(username, limit=limit, offset=offset)


@router.patch("/users/{username}", response_model=UserResponse)
def patch_user_bio(username: str, body: UserBioPatch):
    return users_service.update_bio(username, body.bio)
