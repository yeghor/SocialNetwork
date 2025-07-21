from databases_manager.postgres_manager.database import SessionLocal
from databases_manager.postgres_manager.models import *
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

ModelT = TypeVar("Models", bound=Base)

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

def postgres_error_handler(action: str = "Unknown action with the database"):
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
    try:
        session = SessionLocal()
        return SessionLocal()
    finally:
        await session.aclose()

@postgres_error_handler(action="Refresh model")
async def refresh_model(session: AsyncSession, model_object: ModelT) -> ModelT:
    return await session.refresh(model_object)