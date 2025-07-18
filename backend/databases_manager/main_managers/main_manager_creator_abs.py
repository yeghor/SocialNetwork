from databases_manager.chromaDB_manager.chroma_manager import ChromaService
from databases_manager.postgres_manager.database_utils import PostgresService
from databases_manager.redis_manager.redis_manager import RedisService
from databases_manager.postgres_manager.models import Post
from authorization import jwt_manager

from abc import ABC, abstractmethod
from typing import Type

from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, TypeVar, Generic

# To follow the open closed principle
S = TypeVar("S", bound="MainServiceBase")

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

class MainServiceBase(MainServiceABC):
    """
    To create obj - use async method `initialize()` *Reason - chromaDB async client requires await. But `__init__` can't be async* \n
    Requires created SQLalchemy AsyncSession \n
    Select mode - `"prod"` | `"test"` \n
    After you finish your work with service - AlWAYS call async method finish to commit and close all connections \n
    Take into account that SQLalchemy AsyncSession requires outer close handling - THIS CLASS DOESN'T CLOSE SQLalhemy AsyncSession.
    """

    def __init__(self, Chroma: ChromaService, Redis: RedisService, Postgres: PostgresService):
        self._PostgresService = Postgres
        self._RedisService = Redis
        self._ChromaService = Chroma

        self._JWT = jwt_manager.JWTService

    @classmethod
    async def create(cls, postgres_session: AsyncSession, mode: str = "prod") -> "MainServiceABC":
        """Postgres AsyncSession needs to be closed manualy!"""
        Postgres = PostgresService(session=postgres_session)
        Redis = RedisService(db_pool=mode)
        ChromaDB = await ChromaService.connect(mode=mode)

        return cls(Chroma=ChromaDB, Redis=Redis, Postgres=Postgres)
    
    async def finish(self, commit_postgres: bool = True) -> None:
        # If i'm not mistaken, chromaDB doesn't require connection close
        # Class assume that provided session is handling it's close
        await self._RedisService.finish()
        if commit_postgres: await self._PostgresService.commit_changes()

    
class MainServiceContextManager(Generic[S], MainServiceContextManagerABS):
    """

    To use this context manager - call async crete function
    Example: `async with await MainServiceContextManager[YourServiceType].create(...) as main_service:`
    """

    def __init__(self, main_service: S):
        self.main_service = main_service

    @classmethod
    async def create(cls, MainServiceType: Type[S], postgres_session: AsyncSession, mode: str = "prod") -> "MainServiceContextManager[S]":
        main_service = await MainServiceType.create(postgres_session=postgres_session, mode=mode)
        return cls(main_service=main_service)
    
    async def __aenter__(self) -> S:
        return self.main_service
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.main_service.finish(commit_postgres=not exc_type)