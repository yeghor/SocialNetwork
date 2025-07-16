from databases_manager.chromaDB_manager.chroma_manager import ChromaService
from databases_manager.postgres_manager.database_utils import PostgresService
from databases_manager.redis_manager.redis_manager import RedisService
from databases_manager.main_managers.main_manager_creator_abs import MainServiceBase
from authorization import jwt_manager

from sqlalchemy.ext.asyncio import AsyncSession


class MainServiceSocial(MainServiceBase):
    pass