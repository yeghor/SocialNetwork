from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, text
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
    username: Mapped[str] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(primary_key=True)
    password_hash: Mapped[str]
    joined: Mapped[datetime] = mapped_column(server_default=text("TIMEZONE('utc', now())"))

    posts: Mapped[List["Post"]] = relationship(
        "Post",
        back_populates="owner",
        lazy="selectin"
    )

    comments: Mapped[List["Comment"]] = relationship(
        "Comment",
        back_populates="owner",
        lazy="selectin"
    )

    reposts: Mapped[List["Repost"]] = relationship(
        "Repost",
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

    post_id: Mapped[UUID] = mapped_column(primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)

    # Add constraits!!!
    title: Mapped[str]
    description: Mapped[str]
    text: Mapped[str]
    image_path: Mapped[str] = mapped_column(nullable=True)
    likes: Mapped[int] = mapped_column(default=0)
    published: Mapped[datetime] = mapped_column(server_default=text("TIMEZONE('utc', now())"))
    last_updated: Mapped[datetime] = mapped_column(server_default=text("TIMEZONE('utc', now())"), onupdate=text("TIMEZONE('utc', now())"))

    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="parent_post", lazy="selectin")
    owner: Mapped["User"] = relationship("User", back_populates="posts", lazy="selectin")
    reposts: Mapped[List["Repost"]] = relationship("Repost", back_populates="parent_post", lazy="selectin")


class Repost(Base):
    __tablename__ = "reposts"

    repost_id: Mapped[UUID] = mapped_column(primary_key=True)
    parent_id: Mapped[UUID] = mapped_column(ForeignKey("posts.post_id", ondelete="SET NULL"), nullable=True)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)

    # Add constraits to fields
    text: Mapped[str]
    likes: Mapped[int] = mapped_column(default=0)
    published: Mapped[datetime] = mapped_column(server_default=text("TIMEZONE('utc', now())"))
    last_updated: Mapped[datetime] = mapped_column(server_default=text("TIMEZONE('utc', now())"), onupdate=text("TIMEZONE('utc', now())"))

    parent_post: Mapped["Post"] = relationship("Post", back_populates="reposts", lazy="selectin")
    owner: Mapped["User"] = relationship("User", back_populates="reposts", lazy="selectin")


class Comment(Base):
    __tablename__ = "comments"

    comment_id: Mapped[UUID] = mapped_column(primary_key=True)
    post_id: Mapped[UUID] = mapped_column(ForeignKey("posts.post_id", ondelete="CASCADE"), nullable=False)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    owner_username: Mapped[str] = mapped_column(ForeignKey("users.username", ondelete="SET NULL"), nullable=True)
    parent_comment_id: Mapped[UUID] = mapped_column(ForeignKey("comments.comment_id", ondelete="CASCADE"), nullable=True)

    text: Mapped[str]
    published: Mapped[datetime] = mapped_column(server_default=text("TIMEZONE('utc', now())"))

    parent_comment: Mapped["Comment"] = relationship("Comment", back_populates="replies", remote_side=[comment_id], lazy="selectin")
    replies: Mapped[List["Comment"]] = relationship("Comment", back_populates="parent_comment", lazy="selectin")
    parent_post: Mapped["Post"] = relationship("Post", back_populates="comments", lazy="selectin")
    owner: Mapped["User"] = relationship("User", back_populates="comments", lazy="selectin")