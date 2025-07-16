from databases_manager.chromaDB_manager.chroma_manager import ChromaService
from databases_manager.postgres_manager.database_utils import PostgresService
from databases_manager.redis_manager.redis_manager import RedisService
from authorization import jwt_manager

from abc import ABC, abstractmethod
from typing import Type

from sqlalchemy.ext.asyncio import AsyncSession

class MainServiceABS(ABC):
    @classmethod
    @abstractmethod
    async def create(cls, postgres_session: AsyncSession, mode: str = "prod") -> "MainServiceABS":
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
        Usage: async with await MainServiceContextManager.create(...)
        """

    @abstractmethod
    async def __aenter__(self) -> "MainServiceABS":
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

class MainServiceBase(MainServiceABS):
    """
    To create obj - use async method **initialize** *Reason - chromaDB async client requires await. But __init__ can't be async* \n
    Requires created SQLalchemy AsyncSession \n
    Select mode - "prod" | "test \n
    After you finish your work with service - AlWAYS call async method finish to commit and close all connections \n
    Take into account that SQLalchemy AsyncSession requires outer close handling - THIS CLASS DOESN'T CLOSE SQLalhemy AsyncSession.
    """

    def __init__(self, Chroma: ChromaService, Redis: RedisService, Postgres: PostgresService):
        self._PostgresService = Postgres
        self._RedisService = Redis
        self._ChromaService = Chroma

        self._JWT = jwt_manager.JWTService

    @classmethod
    async def create(cls, postgres_session: AsyncSession, mode: str = "prod") -> "MainServiceABS":
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

    
class MainServiceContextManager(MainServiceContextManagerABS):
    def __init__(self, main_service: MainServiceABS):
        self.main_service = main_service

    @classmethod
    async def create(cls, MainService: Type[MainServiceABS], postgres_session: AsyncSession, mode: str = "prod") -> MainServiceABS:
        main_service = await MainService.create(postgres_session=postgres_session, mode=mode)
        return cls(main_service=main_service)
    
    async def __aenter__(self):
        return self.main_service
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.main_service.finish(commit_postgres=not exc_type)