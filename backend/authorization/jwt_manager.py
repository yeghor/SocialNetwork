import jwt
from dotenv import load_dotenv
from os import getenv
from datetime import datetime
from databases_manager.redis_manager.redis_manager import RedisService
from typing import Dict
from schemas import PayloadJWT, TokenResponseSchema
import jwt.exceptions as jwt_exceptions
from functools import wraps
from fastapi import HTTPException

load_dotenv()

def jwt_error_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if isinstance(e, jwt_exceptions.DecodeError):
                raise HTTPException(status_code=500, detail="JWT Token decoding failed")
            elif isinstance(e, jwt_exceptions.PyJWTError):
                raise HTTPException(status_code=401, detail="Invalid or malformed JWT token")
            else:
                raise HTTPException(status_code=500, detail=f"Uknown error occured (jwt_manager): {e}")
    return wrapper

class JWTService:
    @classmethod
    def prepare_token(cls, jwt_token: str) -> str:
        """
        This method validates and removes "Bearer" prefix from token
        """
        if not jwt_token.startswith("Bearer ") or not jwt_token:
            raise HTTPException(status_code=400, detail="Bad token")
        return jwt_token.removeprefix("Bearer ")

    @classmethod
    @jwt_error_handler
    def generate_token(cls, user_id: str) -> str:
        encoded_jwt = jwt.encode(
            payload={
                "user_id": str(user_id),
                "issued_at": int(datetime.now().timestamp())
            },
            key=getenv("SECRET_KEY"),
            algorithm=getenv("JWT_ALGORITHM")
        )
        return encoded_jwt

    # Doesn't require error handle
    @classmethod
    async def generate_save_token(cls, user_id: str, redis: RedisService) -> TokenResponseSchema:
        encoded_jwt = cls.generate_token(user_id)
        expires_at = await redis.save_jwt(jwt_token=encoded_jwt, user_id=user_id)

        return TokenResponseSchema.model_validate({"token": encoded_jwt, "expires_at": expires_at})

    @classmethod
    @jwt_error_handler
    def extract_jwt_payload(cls, jwt_token: str) -> PayloadJWT:
        payload = jwt.decode(
            jwt=jwt_token,
            key=getenv("SECRET_KEY"),
            algorithms=getenv("JWT_ALGORITHM")
        )
        return PayloadJWT.model_validate(payload)