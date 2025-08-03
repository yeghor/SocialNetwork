import pytest
from databases_manager.postgres_manager.database import create_engine, create_sessionmaker
from databases_manager.postgres_manager.database_utils import get_session
from databases_manager.postgres_manager.models import User, Post, Base
from databases_manager.postgres_manager.postgres_manager import PostgresService
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
from pydantic_schemas.pydantic_schemas_social import PostDataSchemaID
from databases_manager.main_managers.auth_manager import MainServiceAuth
from datetime import datetime


@pytest.mark.asyncio
async def test_postgres_service():    
    engine = create_engine(mode="test")
    session = create_sessionmaker(engine=engine)()

    await drop_all(engine=engine, Base=Base)
    await initialize_models(engine=engine, Base=Base)

    try:
        assert isinstance(session, AsyncSession)

        ps = PostgresService(postgres_session=session)

        uid1 = str(uuid4())
        uid2 = str(uuid4())
        uid3 = str(uuid4())

        pid1 = str(uuid4())
        pid2 = str(uuid4())
        pid3 = str(uuid4())

        user1 = User(
            user_id=uid1,
            image_path=None,
            username="user1",
            email="user1@example.com",
            password_hash=hash_password("password1"),
        )
        user2 = User(
            user_id=uid2,
            image_path=None,
            username="user2",
            email="user2@example.com",
            password_hash=hash_password("password2"),
        )
        user3 = User(
            user_id=uid3,
            image_path=None,
            username="ggg",
            email="user3@example.com",
            password_hash=hash_password("password3"),
        )

        user1.followed.append(user2)
        user1.followed.append(user3)
        user3.followed.append(user2)
        user2.followed.append(user3)

        await ps.insert_models_and_flush(user1, user2, user3)

        post1 = Post(
            post_id=pid1,
            owner_id=user1.user_id,
            parent_post_id=None,
            is_reply=False,
            title="First Post",
            text="This is the first post by user1.",
            image_path=None,
            popularity_rate=5,
        )

        post2 = Post(
            post_id=pid2,
            owner_id=user2.user_id,
            parent_post_id=post1.post_id,
            is_reply=True,
            title="Reply to First Post",
            text="This is a reply to the first post by user2.",
            image_path=None,
            popularity_rate=200,
        )

        post3 = Post(
            post_id=str(uuid4()),
            owner_id=user3.user_id,
            parent_post_id=None,
            is_reply=False,
            title="Another Post",
            text="This is another post by user3.",
            image_path=None,
            popularity_rate=450,
        )

        await ps.insert_models_and_flush(post1, post2, post3)

        assert await ps.get_user_by_id(user_id=uid1) == user1

        # Assume that FEED_MAX_POSTS_LOAD >= 3
        fresh_posts = await ps.get_fresh_posts(user=user1)
        assert len(fresh_posts) == 2
        assert fresh_posts[0] == post3

        assert len(await ps.get_all_from_model(ModelType=User)) == 3

        all_posts = await ps.get_entries_by_ids(ids=[pid1, pid2], ModelType=Post)
        assert post1 in all_posts
        assert post2 in all_posts
        assert post3 not in all_posts

        assert await ps.get_entry_by_id(id_=uid3, ModelType=User) == user3
        
        users = await ps.get_users_by_username(prompt="user")
        assert user1 in users
        assert user2 in users
        assert user3 not in users

        await ps.change_field_and_flush(Model=user3, username="user3", email="user3@newemail.com")
        assert user3.username == "user3"
        assert user3.email == "user3@newemail.com"

        post4 = Post(
            post_id=str(uuid4()),
            owner_id=user2.user_id,
            parent_post_id=None,
            is_reply=False,
            title="Post to delete",
            text="This is another post by user2.",
            image_path=None,
            popularity_rate=423,
        )
        await ps.insert_models_and_flush(post4)
        id_ = post4.post_id
        await ps.delete_models_and_flush(post4)
        assert not await ps.get_entry_by_id(id_=id_, ModelType=Post)

        assert await ps.get_user_by_username_or_email(email=user1.email) == user1
        assert await ps.get_user_by_username_or_email(username=user1.username) == user1

        followed_posts = await ps.get_followed_posts(user=user1)
        assert post2 in followed_posts
        assert post3 in followed_posts
        assert post1 not in followed_posts


        updated_post = await ps.update_post_fields(post_data=PostDataSchemaID(post_id=post3.post_id, title="New title", text="New wonderful text"), return_updated_post=True)
        assert updated_post.title == "New title"
        assert updated_post.text == "New wonderful text"

        ...


    finally:
        await ps.close()
