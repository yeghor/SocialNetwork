from __future__ import annotations

from services.postgres_service.models import ActionType

from pydantic import BaseModel, field_validator, Field, ValidationInfo, model_validator
from uuid import UUID
from datetime import datetime
from typing import List, Any, Annotated
from dotenv import load_dotenv
from os import getenv

load_dotenv()

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
        return str(value)

class UserIDValidate(BaseModel):
    user_id: str

    @field_validator("user_id", mode="before")
    @classmethod
    def validate_id(cls, value: Any):        
        return str(value)

class PostBaseShort(PostIDValidate):
    title: str
    published: datetime
    is_reply: bool

class PostBase(PostBaseShort):
    owner: UserShortSchema | None

    pictures_urls: List[str]

class PostLiteSchema(PostBase):
    parent_post: PostBase | None

# TODO: Separate urls field to diferent models
class PostSchema(PostBase):
    text: str

    likes: int = 0
    views: int = 0

    last_updated: datetime

    parent_post: PostBase | None


# =====================

class UserShortSchema(UserIDValidate):
    username: str

class UserShortSchemaAvatarURL(UserShortSchema):
    avatar_url: str | None
    
    # Boolean variable to identify which messsages do user own
    me: bool

class UserLiteSchema(UserShortSchema):
    """Pass to the followers field List[User]!"""
    followers: List[UserShortSchema]


class UserSchema(UserLiteSchema):
    followed: List[UserShortSchema]
    avatar_url: str | None

# =================
# Body data structure
class PostDataSchemaBase(BaseModel):
    title: str
    text: str
    
class MakePostDataSchema(PostDataSchemaBase):
    parent_post_id: str | None

class PostDataSchemaID(PostDataSchemaBase):
    post_id: str
