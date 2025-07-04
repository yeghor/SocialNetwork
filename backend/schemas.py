from pydantic import BaseModel, field_validator, ValidationInfo
from datetime import datetime
from typing import Any, List
from uuid import UUID

class PayloadJWT(BaseModel):
    user_id: str
    issued_at: datetime

    @field_validator("issued_at", mode="after")
    @classmethod
    def from_unix_to_datetime(cls, value: Any) -> datetime:
        if isinstance(value, int):
            value = datetime.fromtimestamp(value)
        return value

"""
Using short schemas to prevent recursive convertation with SQLalchemy relationship.
"""

# Add constraits!!!
class ShortUserProfileSchema(BaseModel):
    user_id: UUID
    username: str
    joined: datetime

    posts: List["ShortPostSchema"]
    comments: List["ShortCommentSchema"]
    reposts: List["ShortRepostSchema"]

class UserProfileSchema(ShortUserProfileSchema):
    followed: List["ShortUserProfileSchema"]
    followers: List["ShortUserProfileSchema"]

class ShortPostSchema(BaseModel):
    post_id: UUID
    owner_id: UUID

    title: str
    description: str
    text: str
    image_path: str | None
    likes: int
    published: datetime
    last_updated: datetime


class PostSchema(ShortPostSchema):
    comments: List["ShortCommentSchema"]
    owner: "ShortUserProfileSchema"
    reposts: "ShortRepostSchema"


class ShortCommentSchema(BaseModel):
    comment_id: UUID
    post_id: UUID
    owner_id: UUID
    parent_comment_id: UUID | None

    text: str
    published: datetime

class CommentSchema(ShortCommentSchema):
    parent_comment: "ShortCommentSchema"
    replies: List["ShortCommentSchema"]
    parent_post: ShortPostSchema
    owner: ShortUserProfileSchema


class ShortRepostSchema(BaseModel):
    repost_id: UUID
    parent_id: UUID
    owner_id: UUID

    text: str
    likes: int
    published: datetime
    last_updated: datetime

class RepostSchema(ShortRepostSchema):
    parent_post: "ShortPostSchema"
    owner: "ShortUserProfileSchema"