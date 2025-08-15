import redis.asyncio as async_redis
import redis.exceptions as redis_exceptions
from fastapi.exceptions import HTTPException
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
RECOMMEND_POST_AGAING_IN = int(getenv("RECOMMEND_POST_AGAING_IN"))
VIEW_TIMEOUT = int(getenv("VIEW_TIMEOUT"))
IMAGE_VIEW_ACCES_SECONDS = int(getenv("IMAGE_VIEW_ACCES_SECONDS", "5"))

ExcludeType = Literal["search", "feed", "viewed"] # TODO: Change "viewed" to "view"
ImageType = Literal["post", "user"]

def redis_error_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except redis_exceptions.RedisError as e:
            raise HTTPException(status_code=500, detail=f"Action with Redis failed: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Uknown erro while working with Redis occured: {e}")
    return wrapper


class RedisService:
    def get_right_first_exclude_post_prefix(self, exclude_type: ExcludeType) -> str:
        if exclude_type == 'feed':
            return self.__exclude_posts_feed_prefix_1
        elif exclude_type == 'search':
            return self.__exclude_posts_search_prefix_1
        elif exclude_type == 'viewed':
            return self.__exclude_posts_viewed_prefix_1
        else:
            raise ValueError("Invalid exclude_type provided")

    def exclude_post_key_pattern(self, user_id: str, post_id: str, exclude_type: ExcludeType):
        first_prefix = self.get_right_first_exclude_post_prefix(exclude_type=exclude_type)
        return f"{first_prefix}{user_id}{self.__exclude_posts_prefix_2}{post_id}"

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
        
    def __init__(self, db_pool: str = "prod", host: str = "localhost"):
        """
        To switch to the test pool - assign db_pool to "test" \n
        If host equal to None - "localhost"
        """
        try:
            self.__client = async_redis.Redis(
                host=self._define_host(host),
                port=int(getenv("REDIS_PORT")),
                db=self._chose_pool(db_pool),
                decode_responses=True,
            )

            # Jwt
            self.__jwt_acces_prefix = "acces-jwt-token:"
            self.__jwt_refresh_prefix = "refresh-jwt-token:"

            # ========

            # Exclude posts
            # Universal exclude posts second prefix
            self.__exclude_posts_prefix_2 = "-post:"

            self.__exclude_posts_feed_prefix_1 = "exclude-posts-feed-user-"
            self.__exclude_posts_search_prefix_1 = "exclude-posts-search-user-"
            self.__exclude_posts_viewed_prefix_1 = "exclude-posts-viewed-user-"

            # ========
            # Image acces tokens prefix
            self.__post_image_acces_prefix = "post-image-acces:"
            self.__user_image_acces_prefix = "user-image-acces:"
 
            # ========
            self.__split_value_string_by = "-"

        except redis_exceptions.RedisError:
            raise HTTPException(status_code=500, detail="Connection to redis failed")
    
    # ===============
    # JWT tokens logic
    # ==============

    @redis_error_handler
    async def save_acces_jwt(self, jwt_token: str, user_id: str | UUID) -> str:
        await self.__client.setex(
            name=f"{self.__jwt_acces_prefix}{str(jwt_token)}",
            time=ACCES_JWT_EXPIRY_SECONDS,
            value=str(user_id)
        )
        return self._get_expiry(ACCES_JWT_EXPIRY_SECONDS)
    
    @redis_error_handler
    async def save_refresh_jwt(self, jwt_token: str, user_id: str | UUID) -> str:
        await self.__client.setex(
            name=f"{(self.__jwt_refresh_prefix)}{jwt_token}",
            time=REFRESH_JWT_EXPIRY_SECONDS,
            value=str(user_id)
        )
        return self._get_expiry(REFRESH_JWT_EXPIRY_SECONDS)

    @redis_error_handler
    async def refresh_acces_token(self, old_token, new_token: str, user_id: str | UUID) -> str:
        await self.delete_jwt(jwt_token=old_token, token_type="acces")
        await self.__client.setex(
            name=f"{self.__jwt_acces_prefix}{new_token}",
            time=ACCES_JWT_EXPIRY_SECONDS,
            value=str(user_id)
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
    async def get_token_by_user_id(self, user_id: UUID | str, token_type: str) -> str | None:
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

    # ===============
    # Post excluding logic
    # ==============

    @redis_error_handler
    async def clear_exclude(self, exclude_type: ExcludeType, user_id: str) -> None:
        # https://stackoverflow.com/questions/21975228/redis-python-how-to-delete-all-keys-according-to-a-specific-pattern-in-python
        first_prefix = self.get_right_first_exclude_post_prefix(exclude_type=exclude_type)
        keys = [key async for key in self.__client.scan_iter(match=f"{first_prefix}{user_id}*")]
        if keys:
            await self.__client.delete(*keys)

    @redis_error_handler
    async def finish(self) -> None:
        await self.__client.aclose()

    @redis_error_handler
    async def add_exclude_post_ids(self, post_ids: List[str], user_id: str, exclude_type: ExcludeType) -> None:
        for id_ in post_ids:
            pattern = self.exclude_post_key_pattern(user_id=user_id, post_id=id_, exclude_type=exclude_type)
            print(pattern)
            await self.__client.setex(pattern, RECOMMEND_POST_AGAING_IN, id_)

    @redis_error_handler
    async def get_exclude_post_ids(self, user_id: str, exclude_type: ExcludeType) -> List[str]:
        first_prefix = self.get_right_first_exclude_post_prefix(exclude_type=exclude_type)
        return [await self.__client.get(key) async for key in self.__client.scan_iter(match=f"{first_prefix}{user_id}*")]            


    @redis_error_handler
    async def add_view(self, id_: str, user_id: str) -> None:
        pattern = self.exclude_post_key_pattern(user_id=user_id, post_id=id_, exclude_type="viewed")
        await self.__client.setex(pattern, VIEW_TIMEOUT, id_)

    @redis_error_handler
    async def check_view_timeout(self, id_: str, user_id:str) -> bool:
        "Returns True - if view from user timeouted, it means that the view can be counted."
        pattern = self.exclude_post_key_pattern(user_id=user_id, post_id=id_, exclude_type="viewed")
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
            return False

        if image_type == "post":
            pattern = f"{self.__post_image_acces_prefix}{url_image_token}"    
        elif image_type == "user":
            pattern = f"{self.__user_image_acces_prefix}{url_image_token}"

        return await self.__client.get(pattern)
    
    