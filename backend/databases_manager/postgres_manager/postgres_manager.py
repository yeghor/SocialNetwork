from sqlalchemy import select, delete, update, or_, inspect, and_, func
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

FEED_MAX_POSTS_LOAD = int(getenv("FEED_MAX_POSTS_LOAD"))

MAX_FOLLOWED_POSTS_TO_SHOW = int(getenv("MAX_FOLLOWED_POSTS_TO_SHOW"))
RETURN_REPLIES = int(getenv("RETURN_REPLIES"))
LOAD_MAX_USERS_POST = int(getenv("LOAD_MAX_USERS_POST"))

class PostgresService:
    def __init__(self, postgres_session: AsyncSession):
        # We don't need to close session. Because Depends func will handle it in endpoints.
        self.__session = postgres_session

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

    async def delete_models_and_flush(self, *models: Base) -> None:
        for model in models:
            await self.__session.delete(model)
        await self.flush()

    @postgres_error_handler(action="Add model and flush")
    async def insert_models_and_flush(self, *models: Base):
        self.__session.add_all(models)
        await self.__session.flush()

    @postgres_error_handler(action="Get user by id")
    async def get_user_by_id(self, user_id: str) -> User | None:
        result = await self.__session.execute(
            select(User)
            .options(selectinload(User.followed), selectinload(User.followers)) # Manually passing selection load. Because of self ref. m2m2
            .where(User.user_id == user_id)
        )
        return result.scalar()

    @postgres_error_handler(action="Get fresh feed")
    async def get_fresh_posts(self, user: User, exclude_ids: List[str] = [], n: int = FEED_MAX_POSTS_LOAD) -> List[Post]:
        result = await self.__session.execute(
            select(Post)
            .where(and_(Post.owner_id != user.user_id, Post.post_id.not_in(exclude_ids)))
            .order_by(Post.popularity_rate.desc(), Post.published.desc())
            .limit(n)
        )
        return result.scalars().all()

    @postgres_error_handler(action="Get new posts")

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
    async def get_entries_by_ids(self, ids: List[str], ModelType: Type[Models]) -> List[Models]:     
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
            result = await self.__session.execute(
                select(User)
                .where(User.user_id == id_)
                .options(selectinload(User.followers), selectinload(User.followed), selectinload(User.posts))
            )
        elif ModelType == Post:
            result = await self.__session.execute(
                select(Post)
                .where(Post.post_id == id_)
                .options(selectinload(Post.replies))
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

    @postgres_error_handler(action="Delete post by id")
    async def delete_post_by_id(self, id_: str) -> None:
        await self.__session.execute(
            delete(Post)
            .where(Post.post_id == id_)
        )

    @postgres_error_handler(action="Get user by username and email")
    async def get_user_by_username_or_email(self, username: str | None = None, email: str | None = None) -> User:
        if not username and not email:
            raise ValueError("Username and email are None!")

        result = await self.__session.execute(
            select(User)
            .where(or_(User.username == username, User.email == email))
        )
        return result.scalar()
    
    @postgres_error_handler(action="Get followed users posts")
    async def get_followed_posts(self, user: User, n: int, exclude_ids: List[str] = []) -> List[Post]:
        """If user not following anyone - returns empty list"""

        # Getting new user, because merged instances may not include loaded relationships
        if n <= 0:
            raise ValueError("Invalid number of posts requested")
        
        user = await self.get_user_by_id(user_id=user.user_id)

        followed_ids = [followed.user_id for followed in user.followed]

        result = await self.__session.execute(
            select(Post)
            .where(and_(Post.owner_id.in_(followed_ids), Post.post_id.not_in(exclude_ids)))
            .order_by(Post.popularity_rate.desc(), Post.published.desc())
            .limit(n)
        )
        return result.scalars().all()


    @postgres_error_handler(action="Update post values nad return post is needed")
    async def update_post_fields(self, post_data: PostDataSchemaID, return_updated_post: bool = False) -> Post | None:
        post_data_dict = post_data.model_dump(exclude_defaults=True, exclude_none=True, exclude={"post_id"})
        if not post_data_dict:
            return
        
        await self.__session.execute(
            update(Post)
            .where(Post.post_id == post_data.post_id)
            .values(**post_data_dict)
        )
        if return_updated_post:
            result = await self.__session.execute(
                select(Post)
                .where(Post.post_id == post_data.post_id)
                .options(selectinload(Post.replies))
            )
            return result.scalar()

    @postgres_error_handler(action="Get action")
    async def get_actions(self, user_id: str, post_id: str, action_type: ActionType) -> List[PostActions]:
        """Return **list** of actions. Even if you specified `action_type` as single action"""
        result = await self.__session.execute(
            select(PostActions)
            .where(and_(PostActions.owner_id == user_id, PostActions.action == action_type, PostActions.post_id == post_id))
        )
        return result.scalars().all()

    @postgres_error_handler(action="Get actions on post by specified type")
    async def get_post_action_by_type(self, post_id: str, action_type: ActionType) -> List[User]:
        result = await self.__session.execute(
            select(PostActions)
            .where(and_(PostActions.post_id == post_id, PostActions.action == action_type))
            .order_by(PostActions.date.desc())
        )
        return result.scalars().all()
    
    @postgres_error_handler(action="Get user actions by type")
    async def get_user_actions(self, user_id: str, action_type: ActionType, n_most_fresh: int | None, return_posts: bool = False) -> List[PostActions] | List[Post]:
        result = await self.__session.execute(
            select(PostActions)
            .where(and_(PostActions.owner_id == user_id, PostActions.action == action_type))
            .order_by(PostActions.date.desc())
            .limit(n_most_fresh) # limit an integer LIMIT parameter, or a SQL expression that provides an integer result. Pass None to reset it.
        )
        actions = result.scalars().all()

        if return_posts: return [action.post for action in actions]
        else: return actions


    async def get_post_replies(self, post_id: str, n: int = RETURN_REPLIES, exclude_ids: List[str] = []) -> List[Post]:
        likes_subq = (
            select(func.count(PostActions.action_id))
            .where(and_(PostActions.post_id == post_id, PostActions.action == "like"))
            .scalar_subquery()
        )
        result = await self.__session.execute(
            select(Post, likes_subq)
            .where(and_(Post.parent_post_id == post_id, Post.post_id.not_in(exclude_ids)))
            .order_by(Post.published.desc(), Post.popularity_rate.desc(), likes_subq.desc())
            .limit(n)
        )
        return result.scalars().all()
    
    async def get_user_posts(self, user_id: str, n: int = LOAD_MAX_USERS_POST, exclude_ids: List[str] = []):
        result = await self.__session.execute(
            select(Post)
            .where(and_(Post.owner_id == user_id, Post.post_id.not_in(exclude_ids)))
            .limit(LOAD_MAX_USERS_POST)
            .order_by(Post.published.desc())
            .options(selectinload(Post.parent_post))
        )

        return result.scalars().all()