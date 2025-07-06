import pytest
from database.database import create_engine, create_sessionmaker
from database.models import User, Post, Base
from sqlalchemy.orm import close_all_sessions
from main import initialize_models, drop_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from authorization.password_manager import hash_password
from uuid import uuid4

from database.database_utils import (
    get_all_posts,
    get_all_users,
    get_fresh_posts,
    get_n_popular_posts,
    get_subs_posts,
    get_user_by_id,
)

"""Tests postgres and chromaDB"""

@pytest.fixture
async def conn():
    """Creates connection and fills test database with fake data"""
    engine = create_engine(mode="test", echo=True)
    session = create_sessionmaker(engine=engine)

    await drop_all(engine=engine, Base=Base)
    await initialize_models(engine=engine, Base=Base)


    async with session() as connection:
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

        connection.add_all([user_1, user_2, user_3])
        await connection.flush()

        post_1 = Post(owner_id=user_1.user_id, title="First post. Non reply", text="Hello, how is it going?", likes=42)
        post_2 = Post(owner_id=user_2.user_id, title="Second post. Reply to first. Reply", text="Fine! Thx for asking", likes=30, is_reply=True, parent_post_id=post_1.post_id)
        post_3 = Post(owner_id=user_3.user_id, title="Third post. Weekend plans. Non reply", text="Anyone up for hiking this weekend?", likes=15)
        post_4 = Post(owner_id=user_1.user_id, title="Fourth post. Reply to weekend plans. Reply", text="No :( Got plans for next weekend", likes=22, is_reply=True, parent_post_id=post_3.post_id)
        post_5 = Post(owner_id=user_2.user_id, title="Fifth post. Reply to weekend plans. Reply", text="Awesome! I'm with you", likes=18, is_reply=True, parent_post_id=post_3.post_id)
        post_6 = Post(owner_id=user_3.user_id, title="Sixth post (3 layer of replies)", text="I'll call you today.", likes=3, is_reply=True, parent_post_id=post_3.post_id)

        connection.add_all([post_1, post_2, post_3, post_4, post_5, post_6])
        await connection.flush()

        yield connection

@pytest.mark.asyncio
async def test_models(conn):
    session = await anext(conn)
    print(type(session))
    all_users = await get_all_users(session=session)
    all_posts = await get_all_posts(session=session)
