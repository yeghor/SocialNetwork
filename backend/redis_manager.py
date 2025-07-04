import redis.asyncio as redis
import redis.exceptions as redis_exceptions
from fastapi.exceptions import HTTPException
from dotenv import load_dotenv
from os import getenv
from typing import Tuple, Optional, Literal
from functools import wraps

load_dotenv()

def redis_error_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except redis_exceptions.RedisError as e:
            raise HTTPException(status_code=500, detail=f"Action with redis failed: {e}")
    return wrapper


class RedisService:
    @staticmethod
    def _chose_pool(pool: str) -> Literal[0, 1]:
        """0 - Prod pool. 1 - Test pool"""
        if pool == "prod": return 0
        elif pool == "test": return 1
        else:
            raise ValueError("Invalid pool name was chosed")

    @staticmethod
    def _define_host(host: str) -> str:
        if not host: return "lolalhost"
        print(host)
        return host

    def __init__(self, db_pool: str = "prod", host: str = "localhost"):
        """
        To switch to the test pool - assign db_pool to "test" \n
        If host equal to None - host will be "localhost"
        """
        try:
            self.__client = redis.Redis(
                host=self._define_host(host),
                port=6379,
                db=self._chose_pool(db_pool),
                decode_responses=True
            )
            self.__jwt_prefix = "jwt-token:"
        except redis_exceptions.RedisError:
            raise HTTPException(status_code=500, detail="Connection to redis failed.")
    
    @redis_error_handler
    async def save_jwt(self, jwt_token: str, user_id: str) -> None:
        await self.__client.setex(
            name=f"{self.__jwt_prefix}{str(jwt_token)}",
            time=int(getenv("JWT_EXPIRY_SECONDS")),
            value=str(user_id)
        )
    
    @redis_error_handler
    async def get_jwt_time_to_expiry(self, jwt_token: str) -> Optional[int]:
        """Get JWT token time to expiry. If token expired or doesn't exists - return None"""
        result = await self.__client.ttl(f"{self.__jwt_prefix}{jwt_token}")
        if result == -2: return None
        elif result == -1: return None
        return result

    @redis_error_handler
    async def delete_jwt(self, jwt_token: str) -> None:
        await self.__client.delete(f"{self.__jwt_prefix}{jwt_token}")

    @redis_error_handler
    async def check_jwt_existense(self, jwt_token: str) -> bool:
        potential_token = await self.__client.get(f"{self.__jwt_prefix}{str(jwt_token)}")
        return bool(potential_token)