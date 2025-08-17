from databases_manager.postgres_manager.models import *
from databases_manager.main_managers.s3_image_storage import StorageABC, S3Storage, LocalStorage
from authorization import jwt_manager


from abc import ABC, abstractmethod
from typing import Type, Literal
from dotenv import load_dotenv
from os import getenv

from sqlalchemy.ext.asyncio import AsyncSession
from typing import TypeVar, Generic

# To follow the open closed principle with annotations
ServiceType = TypeVar("Services", bound="MainServiceBase")

load_dotenv()
USE_S3_BOOL_STRING = getenv("USE_S3", "True")

class MainServiceABC(ABC):
    @classmethod
    @abstractmethod
    async def create(cls, postgres_session: AsyncSession, mode: str = "prod") -> "MainServiceABC":
        """
        Async method that creates class object
        Choose mode - "prod"/"test"
        """

    @abstractmethod
    async def finish(self, commit_postgres: bool = True) -> None:
        """Async method that closes all connections. ALWAYS cal it after you finish work with class."""

class MainServiceContextManagerABS(ABC):
    @classmethod
    @abstractmethod
    async def create(cls, postgres_session: AsyncSession, mode: str = "prod") -> "MainServiceContextManagerABS":
        """
        Async method to create MainService instance.
        Usage: `async with await MainServiceContextManager.create(...)`
        """

    @abstractmethod
    async def __aenter__(self) -> "MainServiceABC":
        """Returns MainService instance"""

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Closes all connections. If exited by exception - doesn't commit postgres"""


async def create():
    """
    Initialize MainService classes. Like: MainServiceAuth, MainServiceSocial \n
    Requires created SQLalchemy AsyncSession.
    Take into account that SQLalchemy AsyncSession requires outer close handling - THIS CLASS DOESN'T CLOSE SQLalhemy AsyncSession. \n

    """

from databases_manager.chromaDB_manager.chroma_manager import ChromaService
from databases_manager.postgres_manager.postgres_manager import PostgresService
from databases_manager.redis_manager.redis_manager import RedisService

class MainServiceBase(MainServiceABC):

    """
    To create obj - use async method `initialize()` *Reason - chromaDB async client requires await. But `__init__` can't be async* \n
    Requires created SQLalchemy AsyncSession \n
    Select mode - `"prod"` | `"test"` \n
    After you finish your work with service - AlWAYS call async method finish to commit and close all connections \n
    Take into account that SQLalchemy AsyncSession requires outer close handling - THIS CLASS DOESN'T CLOSE SQLalhemy AsyncSession.
    """

    def __init__(self, Chroma: ChromaService, Redis: RedisService, Postgres: PostgresService, ImageStorage: StorageABC):
        self._PostgresService = Postgres
        self._RedisService = Redis
        self._ChromaService = Chroma
        self._ImageStorage = ImageStorage

        self._JWT = jwt_manager.JWTService

    @classmethod
    async def create(cls, postgres_session: AsyncSession, mode: Literal["prod", "test"] = "prod") -> "MainServiceABC":
        """Postgres AsyncSession needs to be closed manualy!"""
        Postgres = PostgresService(postgres_session=postgres_session)
        Redis = RedisService(db_pool=mode)
        ChromaDB = await ChromaService.connect(mode=mode)
    
        prepared_env_use_s3 = USE_S3_BOOL_STRING.lower().strip()

        if prepared_env_use_s3 == "true": Storage = S3Storage(mode=mode)
        elif prepared_env_use_s3 == "false": Storage = LocalStorage(mode=mode, Redis=Redis)
        else: raise ValueError("Invalid USE_S3 dotenv variable value. Read comment #")
        
        return cls(Chroma=ChromaDB, Redis=Redis, Postgres=Postgres, ImageStorage=Storage)
    
    async def finish(self, commit_postgres: bool = True) -> None:
        # If i'm not mistaken, chromaDB doesn't require connection close
        await self._RedisService.finish()
        if commit_postgres: await self._PostgresService.commit_changes()
        else: await self._PostgresService.rollback()
        await self._PostgresService.close()

    
class MainServiceContextManager(Generic[ServiceType], MainServiceContextManagerABS):
    """

    To use this context manager - call async crete function
    Example: `async with await MainServiceContextManager[YourServiceType].create(...) as main_service:`
    """

    def __init__(self, main_service: ServiceType):
        self.main_service = main_service

    @classmethod
    async def create(cls, MainServiceType: Type[ServiceType], postgres_session: AsyncSession, mode: str = "prod") -> "MainServiceContextManager[ServiceType]":
        main_service = await MainServiceType.create(postgres_session=postgres_session, mode=mode)
        return cls(main_service=main_service)
    
    async def __aenter__(self) -> ServiceType:
        return self.main_service
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.main_service.finish(commit_postgres=not exc_type)
        pass