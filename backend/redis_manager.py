import redis.asyncio as redis
import redis.exceptions as redis_exceptions
from fastapi.exceptions import HTTPException
from dotenv import load_dotenv
from os import getenv
from typing import Tuple, Optional

load_dotenv()

def redis_error_handler(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except redis_exceptions.RedisError as e:
            raise HTTPException(status_code=500, detail=f"Action with redis failed: {e}")
    return wrapper

# Needs to be refactored
class RedisService:
    def __init__(self):
        try:
            self.__client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True
            )
        except redis_exceptions.RedisError:
            raise HTTPException(status_code=500, detail="Connection to redis failed.")
    
    @redis_error_handler
    async def save_jwt(self, jwt_token: str, user_id: str) -> None:
        await self.__client.setex(
            name=f"jwt-token:{str(jwt_token)}",
            time=int(getenv("JWT_EXPIRY_SECONDS")),
            value=str(user_id)
        )
    
    @redis_error_handler
    async def get_jwt_time_to_expiry(self, jwt_token: str) -> Optional[int]:
        """Get JWT token time to expiry """
        return await self.__client.getex(name=str(jwt_token))

    @redis_error_handler
    async def delete_jwt(self, jwt_token: str) -> None:
        await self.__client.delete(jwt_token)

    @redis_error_handler
    async def check_jwt_existense(self, jwt_token: str) -> bool:
        potential_token = await self.__client.get(jwt_token)
        return bool(potential_token)