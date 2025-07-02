from main import engine, SessionLocal
from sqlalchemy.ext.asyncio import AsyncSession

async def get_session_depends():
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
