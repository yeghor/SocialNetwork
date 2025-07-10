from pydantic import BaseModel, field_validator, ValidationInfo, Field
from datetime import datetime
from typing import Any, List
from uuid import UUID
from dotenv import load_dotenv
from os import getenv

load_dotenv()

class PayloadJWT(BaseModel):
    user_id: str
    issued_at: datetime

    @field_validator("issued_at", mode="before")
    @classmethod
    def from_unix_to_datetime(cls, value: datetime | int) -> datetime:
        if isinstance(value, int):
            value = datetime.fromtimestamp(value)
        return value
    
    @field_validator("user_id", mode="before")
    @classmethod
    def user_id_to_uuid(cls, value: str | UUID) -> UUID:
        if isinstance(value, str):
            value = UUID(value)
        return value

class TokenProvided(BaseModel):
    token: str

"""
Using short schemas to prevent recursive convertation with SQLalchemy relationship.
"""
# Add constraits!!!
class ShortUserProfileSchema(BaseModel):
    user_id: UUID
    username: str = Field(min_length=int(getenv("USERNAME_MIN_L")), max_length=int(getenv("USERNAME_MAX_L")))
    joined: datetime

class UserProfileSchema(ShortUserProfileSchema):
    posts: List["PostSchema"]
    followed: List["ShortUserProfileSchema"]
    followers: List["ShortUserProfileSchema"]

class ShortPostSchema(BaseModel):
    post_id: UUID
    owner_id: UUID
    parent_post_id: UUID | None

    is_reply: bool

    title: str = Field(min_length=int(getenv("POST_TITLE_MIN_L")), max_length=int(getenv("POST_TITLE_MAX_L")))
    text: str = Field(min_length=int(getenv("POST_TEXT_MIN_L")), max_length=int(getenv("POST_TEXT_MAX_L")))
    image_path: str | None
    likes: int
    published: datetime
    last_updated: datetime


class PostSchema(ShortPostSchema):
    owner: "ShortUserProfileSchema"
    parent_post: "ShortPostSchema"
    replies: List["ShortPostSchema"]
    viewers: List["HistorySchema"]

class HistorySchema(BaseModel):
    owner: "ShortUserProfileSchema"
    post: "ShortPostSchema"