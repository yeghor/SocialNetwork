from __future__ import annotations

from databases_manager.postgres_manager.models import ActionType

from pydantic import BaseModel, field_validator, Field, ValidationInfo, model_validator
from uuid import UUID
from datetime import datetime
from typing import List, Any, Annotated
from dotenv import load_dotenv
from os import getenv

load_dotenv()

POST_TITLE_MAX_L = int(getenv("POST_TITLE_MAX_L", 100))
POST_TITLE_MIN_L = int(getenv("POST_TITLE_MIN_L", 1))

POST_TEXT_MAX_L = int(getenv("POST_TEXT_MAX_L", 1000))
POST_TEXT_MIN_L = int(getenv("POST_TEXT_MIN_L", 1))

class ActionSchemaShort(BaseModel):
    owner_id: str
    post_id: str

    action: ActionType
    date: datetime

class ActionShema(ActionSchemaShort):
    owner: UserShortSchema
    post: PostBaseShort

class PostIDValidate(BaseModel):
    post_id: str

    @field_validator("post_id", mode="before")
    @classmethod
    def validate_id(cls, value: Any):
        print(value)        
        return str(value)

class UserIDValidate(BaseModel):
    user_id: str

    @field_validator("user_id", mode="before")
    @classmethod
    def validate_id(cls, value: Any):        
        return str(value)

class PostBaseShort(PostIDValidate):
    title: str
    image_path: str | None
    published: datetime

class PostBase(PostBaseShort):
    owner: UserShortSchema | None

class PostLiteShortSchema(PostBase):
    parent_post: PostBase | None

class PostSchema(PostBase):
    text: str

    liked_by: List[UserShortSchema] = []
    likes: int = 0
    views: int = 0

    last_updated: datetime

    replies: List[PostLiteShortSchema]

    parent_post: PostBase | None

    # Owner stats. Private field: post_id == user_id
    viewed_by: List[UserShortSchema] | None = None


# =====================

class UserShortSchema(UserIDValidate):
    image_path: str | None
    username: str

class UserLiteSchema(UserShortSchema):
    """Pass to the followers field List[User]!"""
    followers: List[UserShortSchema]


class UserSchema(UserLiteSchema):
    followed: List[UserShortSchema]
    posts: List[PostLiteShortSchema]

# =================
# Body data structure
class PostDataSchemaBase(BaseModel):
    title: str
    text: str
    
class MakePostDataSchema(PostDataSchemaBase):
    parent_post_id: str | None

class PostDataSchemaID(PostDataSchemaBase):
    post_id: str
