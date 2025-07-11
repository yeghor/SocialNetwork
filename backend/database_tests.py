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

from databases_manager.main_databases_manager import MainService

"""Tests postgres and chromaDB"""

@pytest.fixture
def users():
    pass1 = hash_password("password1")
    pass2 = hash_password("password2")
    pass3 = hash_password("password3")

    user_1 = User(username="user1", email="user1@gmail.com", password_hash=pass1)
    user_2 = User(username="user2", email="user2@gmail.com", password_hash=pass2)
    user_3 = User(username="user3", email="user3@gmail.com", password_hash=pass3)

    user_1.followed.append(user_2)
    user_1.followed.append(user_3)
    user_2.followed.append(user_1)
    user_3.followed.append(user_1)

    return [user_1, user_2, user_3]

@pytest.fixture
def posts():
    post_1_id, post_2_id, post_3_id, post_4_id, post_5_id, post_6_id = (uuid4() for _ in range(6))

    post_1 = Post(post_id=post_1_id, title="First post. Non reply", text="Hello, how is it going?", likes=42)
    post_2 = Post(post_id=post_2_id, title="Second post. Reply to first. Reply", text="Fine! Thx for asking", likes=30, is_reply=True, parent_post_id=post_1.post_id)
    post_3 = Post(post_id=post_3_id, title="Third post. Weekend plans. Non reply", text="Anyone up for hiking this weekend?", likes=15)
    post_4 = Post(post_id=post_4_id, title="Fourth post. Reply to weekend plans. Reply", text="No :( Got plans for next weekend", likes=22, is_reply=True, parent_post_id=post_3.post_id)
    post_5 = Post(post_id=post_5_id, title="Fifth post. Reply to weekend plans. Reply", text="Awesome! I'm with you", likes=18, is_reply=True, parent_post_id=post_3.post_id)
    post_6 = Post(post_id=post_6_id, title="Sixth post (3 layer of replies)", text="I'll call you today.", likes=3, is_reply=True, parent_post_id=post_5.post_id)

    return [post_1, post_2, post_3, post_4, post_5, post_6]

@pytest.fixture
async def create_session(users, posts):
    """Creates connection and fills test database with fake data"""
    engine = create_engine(mode="test", echo=True)
    session = create_sessionmaker(engine=engine)

    await drop_all(engine=engine, Base=Base)
    await initialize_models(engine=engine, Base=Base)

    user_1, user_2, user_3 = users
    post_1, post_2, post_3, post_4, post_5, post_6 = posts

    async with session() as connection:
        connection.add_all(users)
        await connection.flush()

        post_1.owner_id = user_1.user_id 
        post_2.owner_id = user_2.user_id
        post_3.owner_id = user_3.user_id
        post_4.owner_id = user_1.user_id
        post_5.owner_id = user_2.user_id

        connection.add_all(posts)
        await connection.flush()

        view_1 = History(post_id=post_1.post_id, user_id=user_1.user_id)
        view_2 = History(post_id=post_2.post_id, user_id=user_1.user_id)
        view_3 = History(post_id=post_2.post_id, user_id=user_1.user_id)

        connection.add_all([view_1, view_2, view_3])
        await connection.flush()

        user_1.views_history.append(view_1)
        user_1.views_history.append(view_2)
        user_1.views_history.append(view_3)

        await connection.commit()
        await connection.aclose()

@pytest.mark.asyncio
async def test_models(create_session):
    session = await get_session()
    service = await MainService.initialize(postgres_session=session, mode="test")

    users = await service.get_all_users()
    
    assert isinstance(users, List)

    await session.aclose()