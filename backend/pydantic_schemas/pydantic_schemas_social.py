from pydantic import BaseModel, field_validator, Field
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

class PostIDValidate(BaseModel):
    post_id: str

    @field_validator("post_id", mode="before")
    @classmethod
    def validate_id(cls, value: Any):
        if type(value) not in (str, UUID):
            raise TypeError("Invalid post_id type. Must be str or UUID")
        
        return str(value)

class UserIDValidate(BaseModel):
    user_id: str

    @field_validator("user_id", mode="before")
    @classmethod
    def validate_id(cls, value: Any):
        if type(value) not in (str, UUID):
            raise TypeError("Invalid post_id type. Must be str or UUID")
        
        return str(value)

class ViewSchema(BaseModel, UserIDValidate, PostIDValidate):
    owner: "UserLiteSchema"


class PostBase(PostIDValidate):
    title:str
    published: str
    image_path: str | None
    is_reply: bool

    owner: "UserLiteSchema"  


class PostLiteShortSchema(PostBase):
    parent_post: PostBase | None

class PostSchema(PostLiteShortSchema):
    text: str

    last_updated: str
    replies: List[PostBase | None]

    liked_by: List["UserLiteSchema" | None]
    viewers: List["UserLiteSchema" | None]


# =====================

class UserLiteSchema(UserIDValidate):
    username: str
    
    # User with len(User.followers/followed)
    followers_count: int
    followed_count: int


class UserSchema(UserLiteSchema):
    followers: List[UserLiteSchema]
    followed: List[UserLiteSchema]

    # Use with datetime.strftime()
    joined: str

    posts: List[PostLiteShortSchema]
    replies: List[PostLiteShortSchema]

# =================
# Body data structure
class PostDataSchemaBase(BaseModel):
    title: str
    text: str
    
class MakePostDataSchema(PostDataSchemaBase):
    parent_post_id: str | None
    is_reply: bool

class PostDataSchemaID(PostDataSchemaBase):
    post_id: str

class UserDataSchema(BaseModel):
    pass