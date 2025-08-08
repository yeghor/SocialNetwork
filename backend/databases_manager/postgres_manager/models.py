from sqlalchemy.orm import DeclarativeBase, Mapped, validates, mapped_column, relationship
from sqlalchemy import ForeignKey, text
from uuid import uuid4
from datetime import datetime
from typing import List
from dotenv import load_dotenv
from os import getenv
import enum


load_dotenv()

def validate_field_range():
    """Soon. To get rid of repetative @validates logic"""

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(primary_key=True)
    image_path: Mapped[str] = mapped_column(nullable=True)
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    joined: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    posts: Mapped[List["Post"]] = relationship(
        "Post",
        back_populates="owner",
        lazy="selectin"
    )

    actions: Mapped[List["PostActions"]] = relationship(
        "PostActions",
        back_populates="owner",
        lazy="selectin"
    )

    # Self referable many-2-many https://stackoverflow.com/questions/9116924/how-can-i-achieve-a-self-referencing-many-to-many-relationship-on-the-sqlalchemy
    followed: Mapped[List["User"]] = relationship(
        "User",
        secondary="friendship", 
        primaryjoin="User.user_id == Friendship.follower_id",
        secondaryjoin="User.user_id == Friendship.followed_id",
        back_populates="followers",
        lazy="selectin"
    )
    followers: Mapped[List["User"]] = relationship(
        "User",
        secondary="friendship",
        primaryjoin="User.user_id == Friendship.followed_id",
        secondaryjoin="User.user_id == Friendship.follower_id",
        back_populates="followed",
        lazy="selectin"
    )

    @validates("username")
    def validate_username(self, key, username: str):
        if not int(getenv("USERNAME_MIN_L")) <= len(username) <= int(getenv("USERNAME_MAX_L")):
            raise ValueError("Username length is out of range")
        return username

    def __repr__(self):
        return f"Username: {self.username}"


class Post(Base):
    __tablename__ = "posts"

    post_id: Mapped[str] = mapped_column(primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    parent_post_id: Mapped[str] = mapped_column(ForeignKey("posts.post_id", ondelete="SET NULL"), nullable=True)    

    is_reply: Mapped[bool] = mapped_column(default=False)

    # Add constraits!!!
    title: Mapped[str] = mapped_column()
    text: Mapped[str]
    published: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    last_updated: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    owner: Mapped["User"] = relationship(
        "User",
        back_populates="posts",
        lazy="selectin"
    )


    popularity_rate: Mapped[int] = mapped_column(default=0)
    last_rate_calculated: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    actions: Mapped[List["PostActions"]] = relationship(
        "PostActions",
        back_populates="post",
        lazy="selectin"
    )


    # Self referable one-2-many relationship https://docs.sqlalchemy.org/en/20/orm/self_referential.html
    parent_post: Mapped["Post"] = relationship(
        "Post",
        back_populates="replies",
        remote_side=[post_id],
        lazy="selectin"
    )

    replies: Mapped[List["Post"]] = relationship(
        "Post",
        back_populates="parent_post",
        lazy="selectin"
    )


    @validates("title")
    def validate_title(self, key, title: str):
        if not int(getenv("POST_TITLE_MIN_L")) <= len(title) <= int(getenv("POST_TITLE_MAX_L")):
            raise ValueError("Post title length is out of range")
        return title

    @validates("text")
    def validate_text(self, key, text: str):
        if not int(getenv("POST_TEXT_MIN_L")) <= len(text) <= int(getenv("POST_TEXT_MAX_L")):
            raise ValueError("Post text length is out of range")
        return text

    def __repr__(self):
        return f"Post name: {self.title} | Rate: {self.popularity_rate}"


# Self referential m2m
class Friendship(Base):
    __tablename__ = "friendship"

    follower_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    followed_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)


class ActionType(enum.Enum):
    view = "view"
    like = "like"
    reply = "reply"
    repost = "repost"


class PostActions(Base):
    __tablename__ = "postactions"

    action_id: Mapped[str] = mapped_column(primary_key=True)

    owner_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    post_id: Mapped[str] = mapped_column(ForeignKey("posts.post_id", ondelete="CASCADE"), primary_key=True)
    action: Mapped[ActionType]
    date: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    post: Mapped[Post] = relationship(
        "Post",
        back_populates="actions",
        lazy="selectin"
    )

    owner: Mapped[User] = relationship(
        "User",
        back_populates="actions",
        lazy="selectin"
    )