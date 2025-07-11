from sqlalchemy.orm import DeclarativeBase, Mapped, validates, mapped_column, relationship
from sqlalchemy import ForeignKey, text
from uuid import UUID, uuid4
from datetime import datetime
from typing import List
from dotenv import load_dotenv
from os import getenv

load_dotenv()

def validate_field_range():
    """Soon. To get rid of repetative @validates logic"""

class Base(DeclarativeBase):
    pass


class Friendship(Base):
    __tablename__ = "friendship"

    follower_id: Mapped[UUID] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    followed_id: Mapped[UUID] = mapped_column(ForeignKey("users.user_id"), primary_key=True)


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    joined: Mapped[datetime] = mapped_column(server_default=text("TIMEZONE('utc', now())"))

    posts: Mapped[List["Post"]] = relationship(
        "Post",
        back_populates="owner",
        lazy="selectin"
    )

    views_history: Mapped[List["History"]] = relationship(
        "History",
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

    post_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    parent_post_id: Mapped[UUID| None] = mapped_column(ForeignKey("posts.post_id", ondelete="SET NULL"), nullable=True)

    is_reply: Mapped[bool] = mapped_column(default=False)

    # Add constraits!!!
    title: Mapped[str] = mapped_column()
    text: Mapped[str]
    image_path: Mapped[str | None] = mapped_column(nullable=True)
    likes: Mapped[int] = mapped_column(default=0)
    published: Mapped[datetime] = mapped_column(server_default=text("TIMEZONE('utc', now())"))
    last_updated: Mapped[datetime] = mapped_column(server_default=text("TIMEZONE('utc', now())"), onupdate=text("TIMEZONE('utc', now())"))

    owner: Mapped["User"] = relationship(
        "User",
        back_populates="posts",
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

    viewers: Mapped[List["History"]] = relationship(
        "History",
        back_populates="post",
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
        return f"Post name: {self.title}"


class History(Base):
    __tablename__ = "history"

    view_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))
    post_id: Mapped[UUID] = mapped_column(ForeignKey("posts.post_id", ondelete="SET NULL"))

    owner: Mapped["User"] = relationship(
        "User",
        back_populates="views_history",
        lazy="selectin"
    )

    post: Mapped["Post"] = relationship(
        "Post",
        back_populates="viewers",
        lazy="selectin"
    )