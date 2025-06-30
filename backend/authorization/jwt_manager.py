import jwt
from dotenv import load_dotenv
from os import getenv
from datetime import datetime
from redis_manager import RedisService
from typing import Dict
from schemas import PayloadJWT
import jwt.exceptions as jwt_exceptions
from functools import wraps
from fastapi import HTTPException

load_dotenv()

def jwt_error_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if isinstance(e, jwt_exceptions.DecodeError):
                raise HTTPException(status_code=500, detail="JWT Token decoding failed")
            elif isinstance(e, jwt_exceptions.PyJWTError):
                raise HTTPException(status_code=401, detail="Invalid or malformed JWT token")
            else:
                raise HTTPException(status_code=500, detail=f"Uknown error occured (jwt_manager): {e}")
    return wrapper

@jwt_error_handler
async def generate_save_token(user_id: str) -> str:
    encoded_jwt = jwt.encode(
        payload={
            "user_id": user_id,
            "issued_at": int(datetime.timestamp())
        },
        key=getenv("SECRET_KEY"),
        algorithm=getenv("JWT_ALGORITHM")
    )
    redis = RedisService()

    await redis.save_jwt(jwt_token=encoded_jwt, user_id=user_id)
    return encoded_jwt

@jwt_error_handler
def extract_jwt_payload(jwt_token: str) -> PayloadJWT:
    payload = jwt.decode(
        jwt=jwt_token,
        key=getenv("SECRET_KEY"),
        algorithms=getenv("JWT_ALGORITHM")
    )
    return PayloadJWT.model_validate(payload)

