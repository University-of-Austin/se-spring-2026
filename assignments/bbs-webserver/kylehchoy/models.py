from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_]+$")


class UserBioPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bio: Optional[str] = Field(default=None, max_length=200)


class PostMessage(BaseModel):
    """Request body for PATCH /posts/{id}. POST /posts uses PostCreate."""
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=500)


class PostCreate(BaseModel):
    """Request body for POST /posts. parent_id is optional — omitted or null
    creates a top-level post; a valid id creates a reply."""
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=500)
    parent_id: Optional[int] = Field(default=None, ge=1)


class UserResponse(BaseModel):
    username: str
    created_at: str
    bio: Optional[str] = None
    post_count: int


class PostResponse(BaseModel):
    id: int
    username: str
    parent_id: Optional[int] = None
    message: str
    created_at: str
    updated_at: Optional[str] = None
    # Always all three kinds, zero-filled. Clients can rely on the keyset
    # existing so they don't need KeyError guards when rendering badges.
    reaction_counts: dict[str, int]


class ReactionsResponse(BaseModel):
    counts: dict[str, int]
    total: int
    # Only populated when the request carries X-Username. Omitted otherwise so
    # anonymous callers don't get a misleading "you have no reactions" field.
    user_reactions: Optional[list[str]] = None
