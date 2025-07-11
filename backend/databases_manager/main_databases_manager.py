from databases_manager.chromaDB_manager.chroma_manager import ChromaService
from databases_manager.postgres_manager.database_utils import PostgresService
from databases_manager.redis_manager.redis_manager import RedisService
from authorization.jwt_manager import JWTService

from databases_manager.postgres_manager.models import User, Post

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from typing import List

class MainService:
    """
    To create obj - use async method **initialize** *Reason - chromaDB async client requires await. But __init__ can't be async* \n
    Requires created SQLalchemy AsyncSession \n
    Select mode - "prod" | "test \n
    After you finish your work with service - AlWAYS call async method finish to commit and close all connections \n
    Take into account that SQLalchemy AsyncSession requires outer close handling.
    """

    def __init__(self, Chroma: ChromaService, Redis: RedisService, Postgres: PostgresService):
        self.__PostgresService = Postgres
        self.__RedisService = Redis
        self.__ChromaService = Chroma

        self.__JWT = JWTService

    @classmethod
    async def initialize(cls, postgres_session: AsyncSession, mode: str = "prod") -> "MainService":
        Postgres = PostgresService(session=postgres_session)
        Redis = RedisService(db_pool=mode)
        ChromaDB = await ChromaService.connect(mode=mode)

        return cls(Chroma=ChromaDB, Redis=Redis, Postgres=Postgres)
    
    async def finish(self, commit_postgres: bool = True) -> None:
        # If i'm not mistaken, chromaDB doesn't require connection close
        await self.__RedisService.finish()
        if commit_postgres: await self.__PostgresService.commit_changes()
        await self.__PostgresService.close()
    
    async def authorize_request_depends(self, token: str, return_user: bool = True) -> User | None:
        """Can be used in fastAPI Depends()"""
        
        valid_token = self.__JWT.prepare_token(jwt_token=token)

        if not await self.__RedisService.check_jwt_existence(jwt_token=valid_token):
            raise HTTPException(status_code=401, detail="Invalid or expires token")
        
        if return_user:
            payload = self.__JWT.extract_jwt_payload(jwt_token=valid_token)
            return await self.__PostgresService.get_user_by_id(payload.user_id)
        
        return None

    async def get_all_users(self) -> List[User]:
        return await self.__PostgresService.get_all_users()