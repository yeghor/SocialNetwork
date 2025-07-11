from databases_manager.chromaDB_manager.chroma_manager import ChromaService
from databases_manager.postgres_manager.database_utils import PostgresService
from databases_manager.redis_manager.redis_manager import RedisService
from authorization import password_manager, jwt_manager
from databases_manager.postgres_manager.models import User, Post
from schemas import (
    RegisterSchema,
    TokenResponseSchema,
    LoginSchema
    )

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

        self.__JWT = jwt_manager.JWTService

    @classmethod
    async def initialize(cls, postgres_session: AsyncSession, mode: str = "prod") -> "MainService":
        Postgres = PostgresService(session=postgres_session)
        Redis = RedisService(db_pool=mode)
        ChromaDB = await ChromaService.connect(mode=mode)

        return cls(Chroma=ChromaDB, Redis=Redis, Postgres=Postgres)
    
    async def finish(self, commit_postgres: bool = True) -> None:
        # If i'm not mistaken, chromaDB doesn't require connection close
        await self.__RedisService.finish()
        if commit_postgres: await self.__PostgresService.commit_changes_and_close()
        await self.__PostgresService.close()
    
    async def authorize_request(self, token: str, return_user: bool = True) -> User | None:
        """Can be used in fastAPI Depends()"""
        
        valid_token = self.__JWT.prepare_token(jwt_token=token)

        if not await self.__RedisService.check_jwt_existence(jwt_token=valid_token):
            raise HTTPException(status_code=401, detail="Invalid or expires token")
        
        if return_user:
            payload = self.__JWT.extract_jwt_payload(jwt_token=valid_token)
            return await self.__PostgresService.get_user_by_id(payload.user_id)
        
        return None

    async def register(self, credentials: RegisterSchema) -> TokenResponseSchema:
        password_hash = password_manager.hash_password(credentials.password)
        print("Creating user model")
        new_user_obj = User(
            username=credentials.username, 
            email=credentials.email,
            password_hash=password_hash
        )
        await self.__PostgresService.insert_model_and_flush(new_user_obj)
        print("Adding user model")

        return await self.__JWT.generate_save_token(new_user_obj.user_id, self.__RedisService)
        
    async def login(self, credentials: LoginSchema):
        pass

    async def get_all_users(self) -> List[User]:
        return await self.__PostgresService.get_all_users()
    
