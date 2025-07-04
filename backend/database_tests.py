import pytest
from database.database import create_engine, create_sessionmaker
from database.models import Base, User
from sqlalchemy.orm import close_all_sessions
from main import initialize_models
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

@pytest.fixture()
async def conn():
    engine = create_engine(mode="test", echo=True)
    session = create_sessionmaker(engine=engine)

    await initialize_models(engine=engine)

    async with session() as connection:
        yield connection

@pytest.mark.asyncio
async def test_models(conn):
    # Draft
    conn = await anext(conn) # Using anext func because it's async generator
    res = await conn.execute(select(User))
    assert res.scalars().all() == []