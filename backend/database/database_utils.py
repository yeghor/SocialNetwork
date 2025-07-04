from main import engine, SessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from models import Base

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
                    detail=F"Unkown error with the database occured: {e} | Action: {action}"
                )
        return wrapper
    return decorator