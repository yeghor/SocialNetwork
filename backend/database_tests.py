import pytest
from databases_manager.postgres_manager.database import create_engine, create_sessionmaker
from databases_manager.postgres_manager.database_utils import get_session
from databases_manager.postgres_manager.models import User, Post, Base
from databases_manager.main_managers.main_manager_creator_abs import MainServiceContextManager
from databases_manager.main_managers.social_manager import MainServiceSocial
from databases_manager.main_managers.auth_manager import MainServiceAuth
from sqlalchemy.orm import close_all_sessions
from main import initialize_models, drop_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from authorization.password_manager import hash_password
from uuid import uuid4
from typing import AsyncGenerator, List
import logging

from databases_manager.main_managers.auth_manager import MainServiceAuth


@pytest.mark.asyncio
async def test_models():
    engine = create_engine(mode="test")
    session = create_sessionmaker(engine=engine)

    async with await MainServiceContextManager[MainServiceAuth].create(postgres_session=session(), MainServiceType=MainServiceAuth) as auth_service:
        pass
