from sqlalchemy import select, delete, update, or_, inspect, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from databases_manager.postgres_manager.models import User, Post, Base, PostActions, ActionType
from databases_manager.postgres_manager.database_utils import postgres_error_handler
from databases_manager.postgres_manager.validate_n_postive import validate_n_postitive
from dotenv import load_dotenv
from os import getenv
from typing import Type, TypeVar, List, Union
from pydantic_schemas.pydantic_schemas_social import PostDataSchemaID
from uuid import UUID

Models = TypeVar("Models", bound=Base)

FEED_MAX_POSTS_LOADED = int(getenv("FEED_MAX_POSTS_LOAD"))
N_MAX_FRESH_POSTS_TO_MIX = int(getenv("N_MAX_FRESH_POSTS_TO_MIX"))

MAX_FOLLOWED_POSTS_TO_SHOW = int(getenv("MAX_FOLLOWED_POSTS_TO_SHOW"))

class PostgresService:
    def __init__(self, session: AsyncSession):
        # We don't need to close session. Because Depends func will handle it in endpoints.
        self.__session = session

    async def close(self) -> None:
        await self.__session.aclose()

    async def commit_changes(self) -> None:
        await self.__session.commit()

    async def rollback(self) -> None:
        await self.__session.rollback()

    async def refresh_model(self, model_obj: Base) -> None:
        await self.__session.refresh(model_obj)

    async def flush(self) -> None:
        await self.__session.flush()

    async def delete_models(self, *models: Base) -> None:
        for model in models:
            await self.__session.delete(model)
        

    @postgres_error_handler(action="Add model and flush")
    async def insert_models_and_flush(self, *models: Base):
        self.__session.add_all(models)
        await self.__session.flush()

    @postgres_error_handler(action="Get user by id")
    async def get_user_by_id(self, user_id: str) -> User | None:
        result = await self.__session.execute(
            select(User)
            .options(selectinload(User.followed), selectinload(User.followers)) # Manually passing selection load. Because of self ref. m2m2
            .where(or_(User.user_id == str(user_id)))
        )
        return result.scalar()

    @validate_n_postitive
    @postgres_error_handler(action="Get fresh feed")
    async def get_fresh_posts(self, user: User) -> List[Post]:
        result = await self.__session.execute(
            select(Post)
            .where(Post.owner_id != user.user_id)
            .order_by(Post.popularity_rate.desc(), Post.published.desc())
            .limit(FEED_MAX_POSTS_LOADED)
        )
        return result.scalars().all()

    # @validate_n_postitive
    # @postgres_error_handler(action="Get subcribers posts")
    # async def get_subscribers_posts(self, n: int, ids, user_models: List[User] | None, most_popular: bool = False) -> List[Post]:
    #     """
    #     Getting posts of users, whose ids mentioned in user_ids or user_models lists. If user_models not empty - getting ids from models.
    #     Most popular sorts posts by descending amount of likes field. Can be used by your followers or who you follow
    #     """
    #     if not ids and not user_models:
    #         return []
    #     if user_models:
    #         ids = [user.user_id for user in user_models]

    #     result = await self.__session.execute(
    #         select(Post)
    #         .where(Post.owner_id.in_(ids))
    #         .order_by(Post.published.desc())
    #         .limit(n)
    #     )
    #     posts = result.scalars().all()
        
    #     if most_popular:
    #         return sorted(posts, key=lambda post : post.likes, reverse=True)

    #     return posts

    @postgres_error_handler(action="Get all posts")
    async def get_all_from_model(self, ModelType: Type[Models]) -> List[Models]:
        result = await self.__session.execute(
            select(ModelType)
        )
        return result.scalars().all()

    @postgres_error_handler(action="Get entries from specific model by ids")
    async def get_entries_by_ids(self, ids: List[str], ModelType: Type[Models], show_replies: bool = True) -> List[Models]:     
        if not ids:
            return []

        if ModelType == User:
            result = await self.__session.execute(
                select(User)
                .where(User.user_id.in_(ids))
            )
        elif ModelType == Post:
            result = await self.__session.execute(
                select(Post)
                .where(Post.post_id.in_(ids))
            )
        else:
            raise TypeError("Unsupported model type!")
        return result.scalars().all()
    
    @postgres_error_handler(action="Get entry from id")
    async def get_entry_by_id(self, id_: str, ModelType: Type[Models]) -> Models:
        if ModelType == User:
            print(id_)
            print(f"Shi? {id_}")
            result = await self.__session.execute(
                select(User)
                .where(User.user_id == id_)
                .options(selectinload(User.followers), selectinload(User.followed), selectinload(User.posts))
            )
        elif ModelType == Post:
            result = await self.__session.execute(
                select(Post)
                .where(Post.post_id == id_)
            )
        else:
            raise TypeError("Unsupported model type!")
        return result.scalar()

    #https://stackoverflow.com/questions/3325467/sqlalchemy-equivalent-to-sql-like-statement
    @postgres_error_handler(action="Get users by LIKE statement")
    async def get_users_by_username(self, prompt: str) -> List[User]:
        if not prompt:
            raise ValueError("Prompt is None")

        result = await self.__session.execute(
            select(User)
            .where(User.username.ilike(f"%{prompt.strip()}%"))
            .options(selectinload(User.followers))
        )
        return result.scalars().all()

    @postgres_error_handler(action="Change field and flush")
    async def change_field_and_flush(self, Model: Models, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(Model, key, value)
        await self.__session.flush()

    @postgres_error_handler(action="Delete posts by id")
    async def delete_posts_by_id(self, ids: List[str]) -> None:
        await self.__session.execute(
            delete(Post)
            .where(Post.post_id.in_(ids))
        )

    @postgres_error_handler(action="Get user by username and email")
    async def get_user_by_username_or_email(self, username: str | None, email: str | None) -> User:
        if not username and not email:
            raise ValueError("Username and email are None!")

        result = await self.__session.execute(
            select(User)
            .where(or_(User.username == username, User.email == email))
        )
        user = result.scalar()
        return user
    
    @postgres_error_handler(action="Get followed users posts")
    async def get_followed_posts(self, user: User) -> List[List[Post]]:
        # Getting new user, because merged instances may not include loaded relationships
        user = await self.get_user_by_id(user_id=user.user_id)

        followed_ids = [followed.user_id for followed in user.followed]

        result = await self.__session.execute(
            select(User)
            .where(User.user_id.in_(followed_ids))
        )
        users = result.scalars().all()

        sorted_posts = [sorted(user.posts, key= lambda x: x.published, reverse=True)[:MAX_FOLLOWED_POSTS_TO_SHOW] for user in users]
        proccesed_posts = []
        for posts in sorted_posts:
            for post in posts:
                if not post.is_reply:
                    proccesed_posts.append(post)
        return proccesed_posts

    @postgres_error_handler(action="Update post values nad return post is needed")
    async def update_post_fields(self, post_data: PostDataSchemaID, post_id: str, return_updated_post: bool = False) -> Post | None:
        post_data_dict = post_data.model_dump(exclude_defaults=True, exclude_none=True, exclude={"post_id"})
        if not post_data_dict:
            return
        
        await self.__session.execute(
            update(Post)
            .where(Post.post_id == post_id)
            .values(**post_data_dict)
        )
        if return_updated_post:
            result = await self.__session.execute(
                select(Post)
                .where(Post.post_id == post_id)
                .options(selectinload(Post.replies))
            )
            return result.scalar()

    @postgres_error_handler(action="Get action")
    async def get_action(self, user_id: str, action_type: ActionType) -> PostActions:
        result = await self.__session.execute(
            select(PostActions)
            .where(and_(PostActions.owner_id == user_id, PostActions.action == action_type))
        )
        return result.scalar()