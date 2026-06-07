import re
from typing import Optional

from pydantic import BaseModel, Field, validator

from db import VALID_REACTIONS


class CreateUser(BaseModel):
    username: str = Field(min_length=3, max_length=20)

    @validator("username")
    def username_allowed_chars(cls, v):
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("username: only letters, digits, and underscores allowed")
        return v


class CreatePost(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    board: Optional[str] = None
    parent_id: Optional[int] = None


class UpdateBio(BaseModel):
    bio: str = Field(max_length=200)


class UpdateMessage(BaseModel):
    message: str = Field(min_length=1, max_length=500)


class CreateBoard(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    description: Optional[str] = None

    @validator("name")
    def name_allowed_chars(cls, v):
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("name: only letters, digits, underscores, and dashes allowed")
        return v


class CreateReaction(BaseModel):
    kind: str

    @validator("kind")
    def kind_must_be_valid(cls, v):
        if v not in VALID_REACTIONS:
            raise ValueError(f"kind must be one of: {', '.join(sorted(VALID_REACTIONS))}")
        return v
