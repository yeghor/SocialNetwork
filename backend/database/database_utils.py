from main import engine, SessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from models import Base, User, Post, Comment
from sqlalchemy import select, or_
from typing import List
from uuid import UUID

def validate_n(func):
    async def wrapper(n: int, *args, **kwargs):
        if n <= 0:
            raise ValueError("Invalid number of entries")
        await func(n, *args, **kwargs)
    return wrapper

async def get_session_depends():
    async with SessionLocal() as conn:
        try:
            yield conn
        finally:
            await conn.close()

def database_error_handler(action: str = "Uknown action with the database"):
    async def decorator(func):
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

@database_error_handler(action="Add model and flush")
async def insert_model_and_flush(session: AsyncSession, *models) -> None:
    """Adding model and making flush"""
    session.add_all(models)
    await session.flush()

@database_error_handler(action="Get user by id")
async def get_user_by_id(session: AsyncSession, user_id: UUID, email: UUID) -> User | None:
    result = await session.execute(
        select(User)
        .where(or_(User.user_id == user_id, User.email == email))
    )
    return result.scalar()

@validate_n
@database_error_handler(action="Get n most popular posts")
async def get_n_popular_posts(session: AsyncSession, n: int) -> List[Post]:
    result = await session.execute(
        select(Post)
        .order_by(Post.likes.desc())
        .limit(n)
    )
    return result.scalars().all()

@validate_n
@database_error_handler(action="Get n most fresh posts")
async def get_fresh_posts(session: AsyncSession, n: int) -> List[Post]:
    result = await session.execute(
        select(Post)
        .order_by(Post.published.desc())
        .limit(n)
    )
    return result.scalars().all()

@validate_n
@database_error_handler(action="Get subcribers posts")
async def get_subs_posts(session: AsyncSession, n: int, user_ids: List[str] | None, user_models: List[User] | None, most_popular: bool = False):
    """
    Getting posts of subcribers, whose ids mentioned in user_ids or user_models lists. If user_models not empty - getting ids from models.
    Most popular sorts posts by descending amount of likes field
    """
    if not user_ids:
        return []

    if user_models:
        user_ids = [user.user_id for user in user_models]

    result = await session.execute(
        select(Post)
        .where(Post.owner_id.in_(user_ids))
        .order_by(Post.published.desc())
        .limit(n)
    )
    posts = result.scalars().all()
    
    if most_popular:
        return sorted(posts, key=lambda post : post.likes, reverse=True)

    return posts

