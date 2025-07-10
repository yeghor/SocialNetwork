from databases_manager.chromaDB_manager.chroma_manager import ChromaService
from databases_manager.postgres_manager.database_utils import PostgresService
from databases_manager.redis_manager.redis_manager import RedisService
from chromadb import AsyncHttpClient

from sqlalchemy.ext.asyncio import AsyncSession

class MainDatabaseService:
    """
    To create obj - use async method **create** *Reason - chromaDB async client requires await. But __init__ can't be async*
    Requires created SQLalchemy AsyncSession
    Select mode - "prod" | "test
    """

    def __init__(self, Chroma: ChromaService, Redis: RedisService, Postgres: PostgresService):
        self.__ChromaService = Chroma
        self.__RedisService = Redis
        self.__ChromaService = Chroma

    @classmethod
    async def initialize(cls, postgres_session: AsyncSession, mode: str = "prod"):
        Postgres = PostgresService(session=postgres_session)
        Redis = RedisService(db_pool="prod1")
        ChromaDB = await ChromaService.connect(postgres_session=postgres_session, mode="prod")

        return cls(Chroma=ChromaDB, Redis=Redis, Postgres=Postgres)

    