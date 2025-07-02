from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey 
from uuid import UUID

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

    followed: Mapped[list["User"]] = relationship(
        "User",
        secondary="friendship",
        primaryjoin="User.user_id == Friendship.follower_id",
        secondaryjoin="User.user_id == Friendship.followed_id",
        back_populates="followers",
        lazy="selectin"
    )
    followers: Mapped[list["User"]] = relationship(
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
    __tablename__ = "post"

    post_id: Mapped[UUID] = mapped_column(primary_key=True)

class Reply(Base):
    __tablename__ = "reply"

    reply_id: Mapped[UUID] = mapped_column(primary_key=True)