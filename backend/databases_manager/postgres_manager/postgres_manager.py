from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from databases_manager.postgres_manager.models import *
from databases_manager.postgres_manager.database_utils import postgres_error_handler, validate_ids_type_to_UUID
from databases_manager.postgres_manager.validate_n_postive import validate_n_postitive
from dotenv import load_dotenv
from os import getenv
from typing import Type, TypeVar

Models = TypeVar("Models", bound=Base)

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

    @postgres_error_handler(action="Add model and flush")
    async def insert_models_and_flush(self, *models: Base):
        self.__session.add_all(models)
        await self.__session.flush()

    @postgres_error_handler(action="Get user by id")
    async def get_user_by_id(self, user_id: UUID) -> User | None:
        result = await self.__session.execute(
            select(User)
            .where(or_(User.user_id == user_id))
        )
        return result.scalar()

    @validate_n_postitive
    @postgres_error_handler(action="Get n most popular posts")
    async def get_n_popular_posts(self, n: int) -> List[Post]:
        result = await self.__session.execute(
            select(Post)
            .order_by(Post.likes.desc())
            .limit(n)
        )
        return result.scalars().all()

    @validate_n_postitive
    @postgres_error_handler(action="Get n most fresh posts")
    async def get_fresh_posts(self, n: int) -> List[Post]:
        result = await self.__session.execute(
            select(Post)
            .order_by(Post.published.desc())
            .limit(n)
        )
        return result.scalars().all()

    @validate_n_postitive
    @postgres_error_handler(action="Get subcribers posts")
    async def get_subscribers_posts(self, n: int, user_ids: List[str] | None, user_models: List[User] | None, most_popular: bool = False) -> List[None] | List[Post]:
        """
        Getting posts of users, whose ids mentioned in user_ids or user_models lists. If user_models not empty - getting ids from models.
        Most popular sorts posts by descending amount of likes field. Can be used by your followers or who you follow
        """
        if user_models:
            user_ids = [user.user_id for user in user_models]
        if not user_ids:
            return []

        result = await self.__session.execute(
            select(Post)
            .where(Post.owner_id.in_(user_ids))
            .order_by(Post.published.desc())
            .limit(n)
        )
        posts = result.scalars().all()
        
        if most_popular:
            return sorted(posts, key=lambda post : post.likes, reverse=True)

        return posts

    """For testcases"""
    @postgres_error_handler(action="Get all users")
    async def get_all_users(self) -> List[User]:
        result = await self.__session.execute(
            select(User)
        )
        return result.scalars().all()

    @postgres_error_handler(action="Get all posts")
    async def get_all_from_model(self, ModelType: Type[Models]) -> List[Models]:
        result = await self.__session.execute(
            select(ModelType)
        )
        return result.scalars().all()

    @validate_ids_type_to_UUID
    @postgres_error_handler(action="Get entries from specific model by ids")
    async def get_entries_by_ids(self, ids: List[UUID | str], ModelType: Type[Models]) -> List[Models]:
        if not ids:
            raise ValueError("Ids is empty")

        for id_ in ids:
            UUID(id_)

        if isinstance(ModelType, User):
            result = await self.__session.execute(
                select(User)
                .where(User.user_id.in_(ids))
            )
        elif isinstance(ModelType, Post):
            result = await self.__session.execute(
                select(Post)
                .where(Post.post_id.in_(ids))
            )
        else:
            raise TypeError("Unsupported model type!")
        return result.scalars().all()
    
    #https://stackoverflow.com/questions/3325467/sqlalchemy-equivalent-to-sql-like-statement
    @postgres_error_handler(action="Get users by LIKE statement")
    async def get_users_by_username(self, prompt: str) -> List[User | None]:
        if not prompt:
            raise ValueError("Prompt is None!")

        result = await self.__session.execute(
            select(User)
            .where(User.username.ilike(f"%{prompt.strip()}%"))
        )
        return result.scalars().all()

    @postgres_error_handler(action="Change field and flush")
    async def change_field_and_flush(self, Model: Base, **kwargs):
        for key, value in kwargs.items():
            setattr(Model, key, value)
        await self.__session.flush()

    @postgres_error_handler(action="Delete models")
    async def delete_models(self, *models):
        pass

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
    async def get_followed_posts(self, user: User) -> List[List[Post] | None]:
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
