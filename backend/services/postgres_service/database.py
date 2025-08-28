from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv
from os import getenv    
from .models import Base
import asyncio
from typing import Tuple

load_dotenv()

RETRIES = int(getenv("RETRIES"))
DELAY = int(getenv("DELAY"))

def define_database_url(mode: str) -> str:
    """ Set mode - "prod" to main database | "test" to test database """
    if mode not in ("prod", "test"):
        raise ValueError("Invalid database mode chosen")
    
    if mode == "prod": return f"postgresql+asyncpg://{getenv('DB_USERNAME')}:{getenv('DB_PASSWORD')}@{getenv('DB_HOST')}:{getenv('DB_PORT')}/{getenv('DB_NAME')}"
    elif mode == "test": return f"postgresql+asyncpg://{getenv('DB_USERNAME_TEST')}:{getenv('DB_PASSWORD_TEST')}@{getenv('DB_HOST_TEST')}:{getenv('DB_PORT_TEST')}/{getenv('DB_NAME_TEST')}"

async def create_engine(mode: str = "prod", echo=False) -> AsyncEngine:
    """ Set mode - "prod" to main database | "test" to test database """
    for i in range(RETRIES):
        try:
            DATABASE_URL = define_database_url(mode)
            print(DATABASE_URL)
            engine = create_async_engine(
                url=DATABASE_URL,
                echo=echo
            )
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            
            return engine
        except Exception:
            print(f"Connection failed or not ready yet. Try:{i+1}")
            await asyncio.sleep(DELAY)
    raise ConnectionError("Failed to connect to postgresSQL")

def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        autoflush=False,
        autocommit=False,
        bind=engine,
    )

async def drop_all(engine: AsyncEngine, Base: Base) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

async def initialize_models(engine: AsyncEngine, Base: Base) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_engine() -> AsyncEngine:
    return await create_engine(mode="prod") 


def get_sessionlocal(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_sessionmaker(engine=engine)