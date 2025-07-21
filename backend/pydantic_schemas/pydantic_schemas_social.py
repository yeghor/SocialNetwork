from pydantic import BaseModel, field_validator
from uuid import UUID
from datetime import datetime
from typing import List, Any

class PostIDValidate(BaseModel):
    post_id: str

    @field_validator(field="post_id", mode="before")
    @classmethod
    def validate_id(cls, value: Any):
        if type(value) not in (str, UUID):
            raise TypeError("Invalid post_id type. Must be str or UUID")
        
        return str(value)

class UserIDValidate(BaseModel):
    user_id: str

    @field_validator(field="post_id", mode="before")
    @classmethod
    def validate_id(cls, value: Any):
        if type(value) not in (str, UUID):
            raise TypeError("Invalid post_id type. Must be str or UUID")
        
        return str(value)

class PostLiteShortSchema(PostIDValidate):
    owner_username: str
    title: str
    likes: int
    is_reply: bool    

    # datetime is not JSON seralizable
    published: str

    # use len(Post.viewers)
    views: int

class PostLiteSchema(PostLiteShortSchema):

    # post relationship
    parent_post: PostLiteShortSchema | None


class PostSchema(PostLiteSchema):
    text: str

    replies: List[PostLiteSchema]

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

class PostDataSchema(BaseModel):
    parent_post_id: str | None

    is_reply: bool

    title: str
    text: str
    
class UserDataSchema(BaseModel):
    pass