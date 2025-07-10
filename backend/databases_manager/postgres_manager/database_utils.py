from main import engine, SessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from databases_manager.postgres_manager.models import *
from sqlalchemy import select, or_
from typing import List
from uuid import UUID

def validate_n_postitive(func):
    @wraps(func)
    async def wrapper(n: int, *args, **kwargs):
        if not isinstance(n, int):
            raise ValueError("Invalid number type")
        if n <= 0:
            raise ValueError("Invalid number of entries")
        return await func(n, *args, **kwargs)
    return wrapper

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
                if isinstance(e, SQLAlchemyError):
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

class PostgresService:
    def __init__(self, session: AsyncSession):
        # We don't need to close session. Because Depends func will handle it in endpoints.
        self.__session = session

    @database_error_handler(action="Add model and flush")
    async def insert_model_and_flush(self, *models: Base) -> None:
        """Adding model and making flush"""
        self.__session.add_all(models)
        await self.__session.flush()

    @database_error_handler(action="Get user by id")
    async def get_user_by_id(self, user_id: UUID, email: str) -> User | None:
        result = await self.__session.execute(
            select(User)
            .where(or_(User.user_id == user_id, User.email == email))
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
    async def get_all_posts(self) -> List[Post]:
        result = await self.__session.execute(
            select(Post)
        )
        return result.scalars().all()

    @validate_ids_type_to_UUID
    @database_error_handler(action="Get posts by ids")
    async def get_posts_by_ids(self, ids: List[UUID | str]):
        result = await self.__session.execute(
            select(Post)
            .where(Post.post_id.in_(ids))
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

    