from ast import pattern
from sqlite3 import _AnyParamWindowAggregateClass
from click import INT
import redis.asyncio as async_redis
import redis.exceptions as redis_exceptions

from exceptions.custom_exceptions import RedisError

from dotenv import load_dotenv
from os import getenv
from typing import Optional, Literal, List
from functools import wraps
from datetime import datetime
from uuid import UUID

load_dotenv()
ACCES_JWT_EXPIRY_SECONDS = int(getenv("ACCES_JWT_EXPIRY_SECONDS"))
REFRESH_JWT_EXPIRY_SECONDS = int(getenv("REFRESH_JWT_EXPIRY_SECONDS"))
DATETIME_BASE_FORMAT = getenv("DATETIME_BASE_FORMAT")

VIEW_TIMEOUT = int(getenv("VIEW_TIMEOUT"))
IMAGE_VIEW_ACCES_SECONDS = int(getenv("IMAGE_VIEW_ACCES_SECONDS"))

EXCLUDE_MAX_VIEWED_POSTS = int(getenv("EXCLUDE_MAX_VIEWED_POSTS"))
EXCLUDE_VIEWED_POSTS_TIMEOUT = int(getenv("EXCLUDE_VIEWED_POSTS_TIMEOUT"))

CHAT_TOKEN_EXPIRY_SECONDS = int(getenv("CHAT_TOKEN_EXPIRY_SECONDS"))

REDIS_HOST = getenv("REDIS_HOST")
REDIS_PORT = int(getenv("REDIS_PORT"))

ImageType = Literal["post", "user"]


def redis_error_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except redis_exceptions.RedisError as e:
            raise RedisError(f"RedisService: RedisError exception occured: {e}")
        except Exception as e:
            raise RedisError(f"RedisService: Uknown exception occured: {e}")
    return wrapper


class RedisService:
    # def _get_right_first_exclude_post_prefix(self, exclude_type: ExcludePostType) -> str:
    #     if exclude_type == 'feed':
    #         return self.__exclude_posts_feed_prefix_1
    #     elif exclude_type == 'search':
    #         return self.__exclude_posts_search_prefix_1
    #     elif exclude_type == 'view':
    #         return self.__exclude_posts_viewed_prefix_1
    #     elif exclude_type == "reply-list":
    #         return self.__exclude_replies_prefix_1
    #     else:
    #         raise ValueError("Invalid exclude_type provided")

    # def _get_right_first_exclude_chat_prefix(self, exclude_type: ChatType) -> str:
    #     if exclude_type == "chat":
    #         return self.__exclude_chat_prefix_1
    #     elif exclude_type == "message":
    #         return self.__exclude_message_prefix_1
    #     elif exclude_type == "not-approved":
    #         return self.__exclude_not_approved_chats_prefix_1
    #     else:
    #         raise ValueError("Invalid exclude-type provided")

    # def exclude_post_key_pattern(self, user_id: str, post_id: str, exclude_type: ExcludePostType):
    #     first_prefix = self._get_right_first_exclude_post_prefix(exclude_type=exclude_type)
    #     return f"{first_prefix}{user_id}{self.__exclude_posts_prefix_2}{post_id}"

    @staticmethod
    def _chose_pool(pool: str) -> Literal[0, 1]:
        """0 - Prod pool. 1 - Test pool"""
        if pool == "prod": return 0
        elif pool == "test": return 1
        else:
            raise ValueError("Invalid pool name was chosed")

    @staticmethod
    def _define_host(host: str) -> str:
        if not host: return "localhost"
        return host

    @staticmethod
    def _get_expiry(SPECIFIC_TOKEN_EXPIRY_IN_SECONDS: int) -> str:
        return datetime.strftime(datetime.fromtimestamp(datetime.utcnow().timestamp() + SPECIFIC_TOKEN_EXPIRY_IN_SECONDS), DATETIME_BASE_FORMAT)
    
    def __init__(self, db_pool: str = "prod"):
        """
        To switch to the test pool - assign db_pool to "test" \n
        If host equal to None - "localhost"
        """

        self.__client = async_redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=self._chose_pool(db_pool),
            decode_responses=True,
        )

        # Jwt
        self.__jwt_acces_prefix = "acces-jwt-token:"
        self.__jwt_refresh_prefix = "refresh-jwt-token:"


        self._viewed_post_prefix = "viewed-posts:"


        # Chat
        self.__chat_token_prefix = "chat-jwt-token:"


        # Image acces tokens prefix
        self.__post_image_acces_prefix = "post-image-acces:"
        self.__user_image_acces_prefix = "user-image-acces:"


    # ===============
    # JWT tokens logic
    # ==============

    @redis_error_handler
    async def save_acces_jwt(self, jwt_token: str, user_id: str) -> str:
        await self.__client.setex(
            name=f"{self.__jwt_acces_prefix}{str(jwt_token)}",
            time=ACCES_JWT_EXPIRY_SECONDS,
            value=user_id
        )
        return self._get_expiry(ACCES_JWT_EXPIRY_SECONDS)
    
    @redis_error_handler
    async def save_refresh_jwt(self, jwt_token: str, user_id: str) -> str:
        await self.__client.setex(
            name=f"{(self.__jwt_refresh_prefix)}{jwt_token}",
            time=REFRESH_JWT_EXPIRY_SECONDS,
            value=user_id
        )
        return self._get_expiry(REFRESH_JWT_EXPIRY_SECONDS)

    @redis_error_handler
    async def refresh_acces_token(self, old_token, new_token: str, user_id: str) -> str:
        await self.delete_jwt(jwt_token=old_token, token_type="acces")
        await self.__client.setex(
            name=f"{self.__jwt_acces_prefix}{new_token}",
            time=ACCES_JWT_EXPIRY_SECONDS,
            value=user_id
        )
        return new_token

    @redis_error_handler    
    async def get_jwt_time_to_expiry(self, jwt_token: str) -> Optional[int]:
        """Get JWT token time to expiry. If token expired or doesn't exists - return None"""
        result = await self.__client.ttl(f"{self.__jwt_acces_prefix}{jwt_token}")
        if result == -2: return None
        elif result == -1: return None
        return result

    @redis_error_handler
    async def delete_jwt(self, jwt_token: str, token_type: str) -> None:
        if not token_type:
            raise ValueError("Token type is None!")
        if token_type == "acces": prefix = self.__jwt_acces_prefix
        elif token_type == "refresh": prefix = self.__jwt_refresh_prefix
   
        await self.__client.delete(f"{prefix}{jwt_token}")

    @redis_error_handler
    async def check_jwt_existence(self, jwt_token: str, token_type: str) -> bool:
        if not jwt_token or not token_type:
            raise ValueError("No jwt_token or token_type provided")

        if token_type == "acces": prefix = self.__jwt_acces_prefix
        elif token_type == "refresh": prefix = self.__jwt_refresh_prefix

        potential_token = await self.__client.get(f"{prefix}{str(jwt_token)}")
        return bool(potential_token)
    
    @redis_error_handler
    async def get_token_by_user_id(self, user_id: str, token_type: str) -> str | None:
        if not user_id or not token_type:
            raise ValueError("user_id or toket_type is None!")

        if token_type == "acces": prefix = self.__jwt_acces_prefix
        elif token_type == "refresh": prefix = self.__jwt_refresh_prefix
        else:
            raise ValueError("Unsuported token type!")

        async for key in self.__client.scan_iter(match=f"{prefix}*"):
            value = await self.__client.get(key)
            if value == str(user_id):
                return key.removeprefix(prefix)

    @redis_error_handler
    async def deactivate_tokens_by_id(self, user_id: str) -> None:
        access_pattern = f"{self.__jwt_acces_prefix}{user_id}"
        refresh_pattern = f"{self.__jwt_refresh_prefix}{user_id}"

        await self.__client.delete(access_pattern, refresh_pattern)

    # # ===============
    # # Post excluding logic
    # # ==============

    # @redis_error_handler
    # async def clear_exclude(self, exclude_type: ExcludePostType, user_id: str) -> None:
    #     # https://stackoverflow.com/questions/21975228/redis-python-how-to-delete-all-keys-according-to-a-specific-pattern-in-python
    #     first_prefix = self._get_right_first_exclude_post_prefix(exclude_type=exclude_type)
    #     keys = [key async for key in self.__client.scan_iter(match=f"{first_prefix}{user_id}*")]
    #     if keys:
    #         await self.__client.delete(*keys)

    # @redis_error_handler
    # async def finish(self) -> None:
    #     await self.__client.aclose()

    # @redis_error_handler
    # async def add_exclude_post_ids(self, post_ids: List[str], user_id: str, exclude_type: ExcludePostType) -> None:
    #     for id_ in post_ids:
    #         pattern = self.exclude_post_key_pattern(user_id=user_id, post_id=id_, exclude_type=exclude_type)
    #         await self.__client.setex(pattern, EXCLUDE_TIMEOUT, id_)

    # @redis_error_handler
    # async def get_exclude_post_ids(self, user_id: str, exclude_type: ExcludePostType) -> List[str]:
    #     first_prefix = self._get_right_first_exclude_post_prefix(exclude_type=exclude_type)
    #     return [await self.__client.get(key) async for key in self.__client.scan_iter(match=f"{first_prefix}{user_id}*")]            


    @redis_error_handler
    async def add_viewed_post(self, ids_: List[str], user_id: str) -> None:
        pattern = f"{self._viewed_post_prefix}{user_id}"
        if await self.__client.llen(pattern) >= EXCLUDE_MAX_VIEWED_POSTS:
            await self.__client.lpop(pattern, count=len(ids_))

        await self.__client.rpush(pattern, *ids_)
        await self.__client.expire(pattern, EXCLUDE_VIEWED_POSTS_TIMEOUT)
        
    @redis_error_handler
    async def get_viewed_posts(self, user_id: str) -> List[str]:
        pattern = f"{self._viewed_post_prefix}{user_id}"
        return await self.__client.get(pattern)

    @redis_error_handler
    async def add_view(self, id_: str, user_id: str) -> None:
        pattern = f"{self.__post_view_timeout_prefix_1}{user_id}{self.__post_view_timeout_prefix_2}{id_}"
        await self.__client.setex(pattern, VIEW_TIMEOUT, id_)

    @redis_error_handler
    async def check_view_timeout(self, id_: str, user_id:str) -> bool:
        "Returns True - if view from user timeouted, it means that the view can be counted."
        pattern = f"{self.__post_view_timeout_prefix_1}{user_id}{self.__post_view_timeout_prefix_2}{id_}"
        return not bool(await self.__client.exists(pattern))
    
    # ===============
    # LocalStorage images token acces
    # ==============

    @redis_error_handler
    async def save_url_user_token(self, image_token: str, image_name: str) -> None:
        pattern = f"{self.__user_image_acces_prefix}{image_token}"
        await self.__client.setex(pattern, IMAGE_VIEW_ACCES_SECONDS, image_name)

    @redis_error_handler
    async def save_url_post_token(self, image_token: str, image_name: str) -> None:
        pattern = f"{self.__post_image_acces_prefix}{image_token}"
        await self.__client.setex(pattern, IMAGE_VIEW_ACCES_SECONDS, image_name)
        
    @redis_error_handler
    async def check_image_access(self, url_image_token: str, image_type: ImageType) -> str | None:
        """
        Returns image name (read ReadMe-dev.md). If acces not granted or token value corrupted - returns None \n
        Pass `n_image` if `image_type` set to "post"
        """
        if not url_image_token:
            return None

        if image_type == "post":
            pattern = f"{self.__post_image_acces_prefix}{url_image_token}"    
        elif image_type == "user":
            pattern = f"{self.__user_image_acces_prefix}{url_image_token}"

        return await self.__client.get(pattern)
    
    # ==============
    # Chat
    # ==============

    # @redis_error_handler
    # async def add_exclude_chat_ids(self, exclude_ids: List[str], user_id: str, exclude_type: ChatType) -> None:
    #     first_prefix = self._get_right_first_exclude_chat_prefix(exclude_type=exclude_type)
    #     for id_ in exclude_ids:
    #         pattern = f"{first_prefix}{user_id}{self.__exclude_chat_prefix_2}{id_}"
    #         await self.__client.set(pattern, id_)

    # @redis_error_handler
    # async def get_exclude_chat_ids(self, user_id: str, exclude_type: ChatType) -> List[str]:
    #     first_prefix = self._get_right_first_exclude_chat_prefix(exclude_type=exclude_type)
    #     return [await self.__client.get(key) async for key in self.__client.scan_iter(match=f"{first_prefix}{user_id}{self.__exclude_chat_prefix_2}*")]


    # # @redis_error_handler
    # async def clear_exclude_chat_ids(self, user_id: str, exclude_type: ChatType) -> None:
    #     # Caution! May not be optimized for large keys numbers
    #     first_prefix = self._get_right_first_exclude_chat_prefix(exclude_type=exclude_type)
    #     to_delete = [key async for key in self.__client.scan_iter(match=f"{first_prefix}{user_id}{self.__exclude_chat_prefix_2}*")]

    #     if to_delete:
    #         await self.__client.delete(*to_delete)    

    @redis_error_handler
    async def save_chat_token(self, chat_token, user_id: str) -> None:
        await self.__client.setex(
            f"{self.__chat_token_prefix}{chat_token}",
            CHAT_TOKEN_EXPIRY_SECONDS,
            user_id
        )

    @redis_error_handler
    async def check_chat_token_existense(self, chat_token: str) -> bool:
        potential_token = await self.__client.get(f"{self.__chat_token_prefix}{chat_token}")
        return bool(potential_token)