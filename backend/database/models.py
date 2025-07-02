from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey 
from uuid import UUID
from datetime import datetime
from typing import List

class Base(DeclarativeBase):
    pass

class Friendship(Base):
    __tablename__ = "friendship"

    follower_id: Mapped[UUID] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    followed_id: Mapped[UUID] = mapped_column(ForeignKey("users.user_id"), primary_key=True)

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    username: Mapped[str]
    password_hash: Mapped[str]
    joined: Mapped[datetime]

    posts: Mapped[List["Post"]] = relationship(
        "Post",
        back_populates="owner",
        lazy="selectin"
    )

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

    def __repr__(self):
        return f"Username: {self.username}"

class Post(Base):
    __tablename__ = "posts"

    post_id: Mapped[str] = mapped_column(primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"))

    # Add constraits to fields
    title: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column()
    text: Mapped[str]
    image_path: Mapped[str] = mapped_column(nullable=True)
    likes: Mapped[int] = mapped_column(default=0)


    # Add relationship
    comments: Mapped[List[]]
    owner: Mapped["User"] = relationship("User", back_populates="posts")


# Think about inheriting posts ?????
class Comment(Post):
    __tablename__ = "comments"
 
class Reply(Base):
    __tablename__ = "replies"

    reply_id: Mapped[UUID] = mapped_column(primary_key=True)