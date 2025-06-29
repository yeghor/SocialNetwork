import redis.asyncio as redis
import redis.exceptions as redis_exceptions
from fastapi.exceptions import HTTPException
from dotenv import load_dotenv
from os import getenv

load_dotenv()

def redis_error_handler(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except redis_exceptions.RedisError as e:
            raise HTTPException(status_code=500, detail=f"Action with redis failed: {e}")
    return wrapper


class RedisService:
    def __init__(self):
        try:
            self.__client = redis.Redis(
                host='localhost',
                port=6379,
                db=0
            )
        except redis_exceptions.RedisError:
            raise HTTPException(status_code=500, detail="Connection to redis failed.")
    
    @redis_error_handler
    async def save_jwt(self, jwt_token: str, user_id: str) -> None:
        await self.__client.setex(
            name=f"user:{str(user_id)}",
            time=int(getenv("JWT_EXPIRY_SECONDS")),
            value=str(jwt_token)
        )
        await self.__client.aclose()