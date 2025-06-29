import jwt
from dotenv import load_dotenv
from os import getenv
from datetime import datetime
from redis_manager import RedisService

load_dotenv()

async def gen_save_token(user_id: str) -> str:
    encoded_jwt = jwt.encode(
        payload={
            "user_id": user_id,
            "issued_at": int(datetime.timestamp())
        },
        key=getenv("SECRET_KEY"),
        algorithm="HS256"
    )
    redis = RedisService()

    await redis.save_jwt(jwt_token=encoded_jwt, user_id=user_id)

