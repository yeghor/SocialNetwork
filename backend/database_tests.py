import pytest
from databases_manager.postgres_manager.database import create_engine, create_sessionmaker
from databases_manager.postgres_manager.database_utils import get_session
from databases_manager.postgres_manager.models import User, Post, History, Base
from sqlalchemy.orm import close_all_sessions
from main import initialize_models, drop_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from authorization.password_manager import hash_password
from uuid import uuid4
from typing import AsyncGenerator, List
import logging

from backend.databases_manager.main_managers.auth_manager import MainServiceAuth


@pytest.mark.asyncio
async def test_models():
    engine = create_engine(mode="test", echo=True)
    session = create_sessionmaker(engine=engine)

    await drop_all(engine=engine, Base=Base)
    await initialize_models(engine=engine, Base=Base)

    async with session() as session:
        service = await MainServiceAuth.create(postgres_session=session, mode="test")
        users = await service.get_all_users()
        
        assert isinstance(users, List)
