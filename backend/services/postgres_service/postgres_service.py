from sqlalchemy import select, delete, update, or_, inspect, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv
from os import getenv
from typing import Type, TypeVar, List, Union, Literal
from pydantic_schemas.pydantic_schemas_social import PostDataSchemaID
from uuid import UUID
from .models import *
from .models import ActionType
from .database_utils import postgres_exception_handler

from exceptions.custom_exceptions import PostgresError

Models = TypeVar("Models", bound=Base)

load_dotenv()

FEED_MAX_POSTS_LOAD = int(getenv("FEED_MAX_POSTS_LOAD"))

MAX_FOLLOWED_POSTS_TO_SHOW = int(getenv("MAX_FOLLOWED_POSTS_TO_SHOW"))
RETURN_REPLIES = int(getenv("RETURN_REPLIES"))
LOAD_MAX_USERS_POST = int(getenv("LOAD_MAX_USERS_POST"))

BASE_PAGINATION = int(getenv("BASE_PAGINATION"))
DIVIDE_BASE_PAG_BY = int(getenv("DIVIDE_BASE_PAG_BY"))
SMALL_PAGINATION = int(getenv("SMALL_PAGINATION"))

class PostgresService:
    def __init__(self, postgres_session: AsyncSession):
        # We don't need to close session. Because Depends func will handle it in endpoints.
        self.__session = postgres_session

    @postgres_exception_handler(action="Close session")
    async def close(self) -> None:
        await self.__session.aclose()

    @postgres_exception_handler(action="Commit session")
    async def commit_changes(self) -> None:
        await self.__session.commit()

    @postgres_exception_handler(action="Rollback session")
    async def rollback(self) -> None:
        await self.__session.rollback()

    @postgres_exception_handler(action="Refresh session model")
    async def refresh_model(self, model_obj: Base) -> None:
        await self.__session.refresh(model_obj)

    @postgres_exception_handler(action="Flush session")
    async def flush(self) -> None:
        await self.__session.flush()

    @postgres_exception_handler(action="Delete model sesion")
    async def delete_models_and_flush(self, *models: Base) -> None:
        for model in models:
            await self.__session.delete(model)
        await self.flush()

    @postgres_exception_handler(action="Add model and flush")
    async def insert_models_and_flush(self, *models: Base):
        self.__session.add_all(models)
        await self.__session.flush()

    @postgres_exception_handler(action="Get user by id")
    async def get_user_by_id(self, user_id: str) -> User | None:
        result = await self.__session.execute(
            select(User)
            .options(selectinload(User.followed), selectinload(User.followers)) # Manually passing selection load. Because of self ref. m2m2
            .where(User.user_id == user_id)
        )
        return result.scalar()

    @postgres_exception_handler(action="Get fresh feed")
    async def get_fresh_posts(self, user: User, page: int, n: int, exclude_ids: List[str]) -> List[Post]:
        result = await self.__session.execute(
            select(Post)
            .where(and_(Post.owner_id != user.user_id, Post.post_id.not_in(exclude_ids)))
            .order_by(Post.popularity_rate.desc(), Post.published.desc())
            .offset((page*n))
            .limit(n)
        )
        return result.scalars().all()

    @postgres_exception_handler(action="Get all posts")
    async def get_all_from_model(self, ModelType: Type[Models]) -> List[Models]:
        result = await self.__session.execute(
            select(ModelType)
        )
        return result.scalars().all()

    @postgres_exception_handler(action="Get entries from specific model by ids")
    async def get_entries_by_ids(self, ids: List[str], ModelType: Type[Models]) -> List[Models]:     
        if not ids:
            return []

        if ModelType == User:
            result = await self.__session.execute(
                select(User)
                .where(User.user_id.in_(ids))
                .options(selectinload(User.followed), selectinload(User.followers))
            )
        elif ModelType == Post:
            result = await self.__session.execute(
                select(Post)
                .where(Post.post_id.in_(ids))
            )
        else:
            raise TypeError("Unsupported model type!")
        return result.scalars().all()
    
    @postgres_exception_handler(action="Get entry from id")
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

    # https://stackoverflow.com/questions/3325467/sqlalchemy-equivalent-to-sql-like-statement
    @postgres_exception_handler(action="Get users by LIKE statement")
    async def get_users_by_username(self, prompt: str, page: int, n: int) -> List[User]:
        print(prompt)
        result = await self.__session.execute(
            select(User)
            .where(User.username.ilike(f"%{prompt.strip()}%"))
            .options(selectinload(User.followers))
            .offset((page*n))
            .limit(n)
        )
        return result.scalars().all()

    @postgres_exception_handler(action="Change field and flush")
    async def change_field_and_flush(self, model: Base, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(model, key, value)
        await self.__session.flush()

    @postgres_exception_handler(action="Delete post by id")
    async def delete_post_by_id(self, id_: str) -> None:
        await self.__session.execute(
            delete(Post)
            .where(Post.post_id == id_)
        )

    @postgres_exception_handler(action="Get user by username and email")
    async def get_user_by_username_or_email(self, username: str | None = None, email: str | None = None) -> User:
        if not username and not email:
            raise ValueError("Username AND email are None!")

        result = await self.__session.execute(
            select(User)
            .where(or_(User.username == username, User.email == email))
        )
        return result.scalar()
    
    @postgres_exception_handler(action="Get followed users posts")
    async def get_followed_posts(self, user: User, n: int, page: int, exclude_ids: List[str] = []) -> List[Post]:
        """If user not following anyone - returns empty list"""

        # Getting new user, because merged instances may not include loaded relationships
        user = await self.get_user_by_id(user_id=user.user_id)

        followed_ids = [followed.user_id for followed in user.followed]

        result = await self.__session.execute(
            select(Post)
            .where(and_(Post.owner_id.in_(followed_ids), Post.post_id.not_in(exclude_ids)))
            .order_by(Post.popularity_rate.desc(), Post.published.desc())
            .offset(page*n)
            .limit((page*n) + n)
        )
        return result.scalars().all()


    @postgres_exception_handler(action="Update post values nad return post is needed")
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

    @postgres_exception_handler(action="Get action")
    async def get_actions(self, user_id: str, post_id: str, action_type: ActionType) -> List[PostActions]:
        """Return **list** of actions ordered by date in descending order. Even if you specified `action_type` as single action"""
        result = await self.__session.execute(
            select(PostActions)
            .where(and_(PostActions.owner_id == user_id, PostActions.action == action_type, PostActions.post_id == post_id))
            .order_by(PostActions.date.desc())
        )
        return result.scalars().all()

    @postgres_exception_handler(action="Get actions on post by specified type")
    async def get_post_action_by_type(self, post_id: str, action_type: ActionType) -> List[User]:
        result = await self.__session.execute(
            select(PostActions)
            .where(and_(PostActions.post_id == post_id, PostActions.action == action_type))
            .order_by(PostActions.date.desc())
        )
        return result.scalars().all()
    
    @postgres_exception_handler(action="Get user actions by type")
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

    @postgres_exception_handler(action="Get post replies")
    async def get_post_replies(self, post_id: str, page: int, n: int) -> List[Post]:
        likes_subq = (
            select(func.count(PostActions.action_id))
            .where(and_(PostActions.post_id == post_id, PostActions.action == "like"))
            .scalar_subquery()
        )
        result = await self.__session.execute(
            select(Post, likes_subq)
            .where(Post.parent_post_id == post_id)
            .order_by(Post.published.desc(), Post.popularity_rate.desc(), likes_subq.desc())
            .offset(page*n)
            .limit(n)
        )
        return result.scalars().all()
    
    @postgres_exception_handler(action="Get user's posts")
    async def get_user_posts(self, user_id: str, page: int, n: int):
        result = await self.__session.execute(
            select(Post)
            .where(and_(Post.owner_id == user_id))
            .limit(LOAD_MAX_USERS_POST)
            .order_by(Post.published.desc())
            .options(selectinload(Post.parent_post))
            .offset(page*n)
            .limit(n)
        )
        return result.scalars().all()

    @postgres_exception_handler(action="Get chat room by it's id")
    async def get_chat_room(self, room_id: str) -> ChatRoom:
        result = await self.__session.execute(
            select(ChatRoom)
            .where(ChatRoom.room_id == room_id)
        )
        return result.scalar()
    
    @postgres_exception_handler(action="Get dialogue chat by two users")
    async def get_dialogue_by_users(self, user_1: User, user_2: User) -> ChatRoom | None:
        result = await self.__session.execute(
            select(ChatRoom)
            .where(and_(ChatRoom.is_group == False, ChatRoom.participants.contains(user_1), ChatRoom.participants.contains(user_2)))
        )
        return result.scalar()

    @postgres_exception_handler(action="Get n chat room messages excluding exclude_ids list")
    async def get_chat_n_fresh_chat_messages(self, room_id: str, page: int,  n: int = int(getenv("MESSAGES_BATCH_SIZE", "50")), pagination_normalization: int = 0) -> List[Message]:
        result = await self.__session.execute(
            select(Message)
            .where(Message.room_id == room_id)
            .order_by(Message.sent.desc())
            .offset((page*n) + pagination_normalization)
            .limit(n)
        )
        return result.scalars().all()
    
    @postgres_exception_handler(action="Get n user chat rooms excluding exclude_ids list")
    async def get_n_user_chats(self, user: User, n, page: int, pagination_normalization: int, chat_type: Literal["chat", "not-approved"]) -> List[ChatRoom]:
        if chat_type == "chat":
            where_stmt = ChatRoom.approved.is_(True)
        elif chat_type == "not-approved":
            where_stmt = ChatRoom.approved.is_(False)

        result = await self.__session.execute(
            select(ChatRoom)
            .where(and_(ChatRoom.participants.contains(user), where_stmt))
            .order_by(ChatRoom.last_message_time.desc())
            .offset((page*n) + pagination_normalization)
            .limit(n)
        )

        return result.scalars().all() 

    @postgres_exception_handler(action="Get message by it's id")
    async def get_message_by_id(self, message_id: str) -> Message | None:
        result = await self.__session.execute(
            select(Message)
            .where(Message.message_id == message_id)
        )

        return result.scalar()