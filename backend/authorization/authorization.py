from fastapi import HTTPException, Header
from backend.databases_manager.redis_manager.redis_manager import RedisService

async def authorize_depends(jwt_token: str = Header()):
    pass

async def authorize_token(jwt_token: str) -> None:
    redis = RedisService()
    existense = redis.check_jwt_existense(jwt_token)
    if not existense:
        raise HTTPException(status_code=401, detail="Unauthorized (Invalid token)")