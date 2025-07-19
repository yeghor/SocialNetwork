from databases_manager.postgres_manager.database import SessionLocal
from databases_manager.postgres_manager.models import *
from databases_manager.main_managers.social_manager import T
from databases_manager.postgres_manager.validate_n_postive import validate_n_postitive

from sqlalchemy.ext.asyncio import AsyncSession

from functools import wraps
from sqlalchemy.exc import SQLAlchemyError, MultipleResultsFound
from fastapi import HTTPException

from sqlalchemy import select, or_
from typing import List, Type, TypeVar
from uuid import UUID


from dotenv import load_dotenv
from os import getenv
import random

MAX_FOLLOWED_POSTS_TO_SHOW = int(getenv("MAX_FOLLOWED_POSTS_TO_SHOW"))

T = TypeVar("T", bound=Base)

def validate_ids_type_to_UUID(func):
    @wraps(func)
    async def wrapper(ids: List[UUID | str],  *args, **kwargs):
        if not ids: 
            raise ValueError(f"Empty ids list")
        ids_validated = []
        for id in ids:
            if isinstance(id, str):
                id = UUID(id)
            elif isinstance(id, UUID):
                pass
            else:
                raise ValueError(f"Invalid id type: {type(id)}")
            ids_validated.append(id)
        return await func(ids_validated, *args, **kwargs)
    return wrapper

async def get_session_depends():
    """
    Automatically closes session.\n
    Use with fastAPI Depends()!
    """
    async with SessionLocal() as conn:
        yield conn

def database_error_handler(action: str = "Unknown action with the database"):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if isinstance(e, MultipleResultsFound):
                    raise HTTPException(
                        status_code=500,
                        detail=f"Unexpectedly, multiply database entries found. Please, contact us and try again later."
                    )
                elif isinstance(e, SQLAlchemyError):
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error with the database occured: {e} | Action: {action}"
                    )
                raise HTTPException(
                    status_code=500,
                    detail=f"Unkown error with the database occured: {e} | Action: {action}"
                )
        return wrapper
    return decorator

async def get_session() -> AsyncSession:
    return SessionLocal()

class PostgresService:
    def __init__(self, session: AsyncSession):
        # We don't need to close session. Because Depends func will handle it in endpoints.
        self.__session = session

    async def close(self) -> None:
        await self.__session.aclose()

    async def commit_changes(self) -> None:
        await self.__session.commit()

    async def rollback(self) -> None:
        await self.__session.rollback()

    @database_error_handler(action="Add model and flush")
    async def insert_models_and_flush(self, *models: Base):
        self.__session.add_all(models)
        await self.__session.flush()

    @database_error_handler(action="Get user by id")
    async def get_user_by_id(self, user_id: UUID) -> User | None:
        result = await self.__session.execute(
            select(User)
            .where(or_(User.user_id == user_id))
        )
        return result.scalar()

    @validate_n_postitive
    @database_error_handler(action="Get n most popular posts")
    async def get_n_popular_posts(self, n: int) -> List[Post]:
        result = await self.__session.execute(
            select(Post)
            .order_by(Post.likes.desc())
            .limit(n)
        )
        return result.scalars().all()

    @validate_n_postitive
    @database_error_handler(action="Get n most fresh posts")
    async def get_fresh_posts(self, n: int) -> List[Post]:
        result = await self.__session.execute(
            select(Post)
            .order_by(Post.published.desc())
            .limit(n)
        )
        return result.scalars().all()

    @validate_n_postitive
    @database_error_handler(action="Get subcribers posts")
    async def get_subscribers_posts(self, n: int, user_ids: List[str] | None, user_models: List[User] | None, most_popular: bool = False) -> List[None] | List[Post]:
        """
        Getting posts of users, whose ids mentioned in user_ids or user_models lists. If user_models not empty - getting ids from models.
        Most popular sorts posts by descending amount of likes field. Can be used by your followers or who you follow
        """
        if user_models:
            user_ids = [user.user_id for user in user_models]
        if not user_ids:
            return []

        result = await self.__session.execute(
            select(Post)
            .where(Post.owner_id.in_(user_ids))
            .order_by(Post.published.desc())
            .limit(n)
        )
        posts = result.scalars().all()
        
        if most_popular:
            return sorted(posts, key=lambda post : post.likes, reverse=True)

        return posts

    """For testcases"""
    @database_error_handler(action="Get all users")
    async def get_all_users(self) -> List[User]:
        result = await self.__session.execute(
            select(User)
        )
        return result.scalars().all()

    @database_error_handler(action="Get all posts")
    async def get_all_from_model(self, ModelType: Type[T]) -> List[T]:
        result = await self.__session.execute(
            select(ModelType)
        )
        return result.scalars().all()

    @validate_ids_type_to_UUID
    @database_error_handler(action="Get entries from specific model by ids")
    async def get_entries_by_ids(self, ids: List[UUID | str], ModelType: Type[T]) -> List[T]:
        if not ids:
            raise ValueError("Ids is empty")

        for id_ in ids:
            UUID(id_)

        if isinstance(ModelType, User):
            result = await self.__session.execute(
                select(User)
                .where(User.user_id.in_(ids))
            )
        elif isinstance(ModelType, Post):
            result = await self.__session.execute(
                select(Post)
                .where(Post.post_id.in_(ids))
            )
        else:
            raise TypeError("Unsupported model type!")
        return result.scalars().all()
    
    #https://stackoverflow.com/questions/3325467/sqlalchemy-equivalent-to-sql-like-statement
    @database_error_handler(action="Get users by LIKE statement")
    async def get_users_by_username(self, prompt: str) -> List[User | None]:
        if not prompt:
            raise ValueError("Prompt is None!")

        result = await self.__session.execute(
            select(User)
            .where(User.username.ilike(f"%{prompt.strip()}%"))
        )
        return result.scalars().all()

    @database_error_handler(action="Change field and flush")
    async def change_field_and_flush(self, Model: Base, **kwargs):
        for key, value in kwargs.items():
            setattr(Model, key, value)
        await self.__session.flush()

    @database_error_handler(action="Delete models")
    async def delete_models(self, *models):
        pass

    @database_error_handler(action="Get user by username and email")
    async def get_user_by_username_or_email(self, username: str | None, email: str | None) -> User:
        if not username and not email:
            raise ValueError("Username and email are None!")

        result = await self.__session.execute(
            select(User)
            .where(or_(User.username == username, User.email == email))
        )
        user = result.scalar()
        return user
    
    @database_error_handler(action="Get followed users posts")
    async def get_followed_posts(self, user: User) -> List[List[Post] | None]:
        followed_ids = [followed.user_id for followed in user.followed]
        
        result = await self.__session.execute(
            select(User)
            .where(User.user_id.in_(followed_ids))
        )
        users = result.scalars().all()

        sorted_posts = [sorted(user.posts, key= lambda x: x.published, reverse=True)[:MAX_FOLLOWED_POSTS_TO_SHOW] for user in users]
        proccesed_posts = []
        for posts in sorted_posts:
            for post in posts:
                if not post.is_reply:
                    proccesed_posts.append(post)
        return proccesed_posts