import pytest
from services.postgres_service import PostgresService, create_engine, create_async_engine, Base, User, Post, PostActions, create_sessionmaker, ActionType

from post_popularity_rate_task.popularity_rate import POST_ACTIONS
from services.core_services import MainServiceContextManager

from main import initialize_models, drop_all
from sqlalchemy.ext.asyncio import AsyncSession
from authorization.password_utils import hash_password
from uuid import uuid4
from pydantic_schemas.pydantic_schemas_social import PostDataSchemaID


@pytest.mark.asyncio
async def test_postgres_service():    
    engine = await create_engine(mode="test")
    session = create_sessionmaker(engine=engine)()

    await drop_all(engine=engine, Base=Base)
    await initialize_models(engine=engine, Base=Base)

    # try:
    #     assert isinstance(session, AsyncSession)

    #     ps = PostgresService(postgres_session=session)

    #     uid1 = str(uuid4())
    #     uid2 = str(uuid4())
    #     uid3 = str(uuid4())

    #     pid1 = str(uuid4())
    #     pid2 = str(uuid4())
    #     pid3 = str(uuid4())

    #     user1 = User(
    #         user_id=uid1,
    #         username="user1",
    #         email="user1@example.com",
    #         password_hash=hash_password("password1"),
    #     )
    #     user2 = User(
    #         user_id=uid2,
    #         username="user2",
    #         email="user2@example.com",
    #         password_hash=hash_password("password2"),
    #     )
    #     user3 = User(
    #         user_id=uid3,
    #         username="ggg",
    #         email="user3@example.com",
    #         password_hash=hash_password("password3"),
    #     )

    #     user1.followed.append(user2)
    #     user1.followed.append(user3)
    #     user3.followed.append(user2)
    #     user2.followed.append(user3)

    #     await ps.insert_models_and_flush(user1, user2, user3)

    #     post1 = Post(
    #         post_id=pid1,
    #         owner_id=user1.user_id,
    #         parent_post_id=None,
    #         is_reply=False,
    #         title="First Post",
    #         text="This is the first post by user1.",
    #         popularity_rate=5,
    #     )

    #     post2 = Post(
    #         post_id=pid2,
    #         owner_id=user2.user_id,
    #         parent_post_id=post1.post_id,
    #         is_reply=True,
    #         title="Reply to First Post",
    #         text="This is a reply to the first post by user2.",
    #         popularity_rate=0,
    #     )

    #     post3 = Post(
    #         post_id=str(uuid4()),
    #         owner_id=user3.user_id,
    #         parent_post_id=None,
    #         is_reply=False,
    #         title="Another Post",
    #         text="This is another post by user3.",
    #         popularity_rate=450,
    #     )

    #     await ps.insert_models_and_flush(post1, post2, post3)

    #     assert await ps.get_user_by_id(user_id=uid1) == user1

    #     # Assume that FEED_MAX_POSTS_LOAD >= 3
    #     fresh_posts = await ps.get_fresh_posts(user=user1)
    #     assert len(fresh_posts) == 2
    #     assert fresh_posts[0] == post3

    #     assert len(await ps.get_all_from_model(ModelType=User)) == 3

    #     all_posts = await ps.get_entries_by_ids(ids=[pid1, pid2], ModelType=Post)
    #     assert post1 in all_posts
    #     assert post2 in all_posts
    #     assert post3 not in all_posts

    #     assert await ps.get_entry_by_id(id_=uid3, ModelType=User) == user3
        
    #     users = await ps.get_users_by_username(prompt="user")
    #     assert user1 in users
    #     assert user2 in users
    #     assert user3 not in users

    #     await ps.change_field_and_flush(model=user3, username="user3", email="user3@newemail.com")
    #     assert user3.username == "user3"
    #     assert user3.email == "user3@newemail.com"

    #     post4 = Post(
    #         post_id=str(uuid4()),
    #         owner_id=user2.user_id,
    #         parent_post_id=None,
    #         is_reply=False,
    #         title="Post to delete",
    #         text="This is another post by user2.",
    #         popularity_rate=423,
    #     )
    #     await ps.insert_models_and_flush(post4)
    #     id_ = post4.post_id
    #     await ps.delete_models_and_flush(post4)
    #     assert not await ps.get_entry_by_id(id_=id_, ModelType=Post)

    #     assert await ps.get_user_by_username_or_email(email=user1.email) == user1
    #     assert await ps.get_user_by_username_or_email(username=user1.username) == user1

    #     followed_posts = await ps.get_followed_posts(user=user1, n=10)
    #     assert post2 in followed_posts
    #     assert post3 in followed_posts
    #     assert post1 not in followed_posts


    #     updated_post = await ps.update_post_fields(post_data=PostDataSchemaID(post_id=post3.post_id, title="New title", text="New wonderful text"), return_updated_post=True)
    #     assert updated_post.title == "New title"
    #     assert updated_post.text == "New wonderful text"

    #     aid1 = str(uuid4())
    #     aid2 = str(uuid4())

    #     action1 = PostActions(action_id=aid1, post_id=post2.post_id, owner_id=user1.user_id, action=ActionType.view, post=post2)
    #     action2 = PostActions(action_id=aid2, post_id=post2.post_id, owner_id=user3.user_id, action=ActionType.like, post=post2)

    #     await ps.insert_models_and_flush(action1, action2)

    #     p2 = await ps.get_entry_by_id(id_=post2.post_id, ModelType=Post)
    #     assert p2.actions == [action1, action2]
        
    #     action = await ps.get_actions(user_id=user3.user_id, post_id=post2.post_id, action_type=ActionType.like)
    #     assert action[0].action_id == action2.action_id

    #     actions = await ps.get_post_action_by_type(post_id=pid2, action_type=ActionType.view)
    #     assert actions[0] == action1

    #     actions = await ps.get_user_actions(user_id=uid3, action_type=ActionType.like, n_most_fresh=1, return_posts=False)
    #     posts = await ps.get_user_actions(user_id=uid3, action_type=ActionType.like, n_most_fresh=1, return_posts=True)

    #     assert actions[0].owner_id == user3.user_id
    #     assert posts[0].post_id == post2.post_id

    # finally:
    #     await ps.close()
