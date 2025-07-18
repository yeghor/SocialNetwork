from databases_manager.chromaDB_manager.chroma_manager import ChromaService
from databases_manager.postgres_manager.database_utils import PostgresService
from databases_manager.redis_manager.redis_manager import RedisService
from databases_manager.main_managers.main_manager_creator_abs import MainServiceBase
from databases_manager.postgres_manager.models import User, Post
from authorization import jwt_manager

from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv
from os import getenv
from typing import List

load_dotenv()


class MainServiceSocial(MainServiceBase):
    async def sync_data(self) -> None:
        posts = await self._PostgresService.get_all_posts()
        await self._ChromaService.add_posts_data(posts=posts)

    async def get_all_posts(self) -> List[Post]:
        return await self._PostgresService.get_all_posts()

    async def get_related_posts(self, user: User) -> List[Post]:
        """
        Returns related posts to provided User table object view history
        """
        post_UUIDS = await self._ChromaService.get_n_related_posts_ids(user=user)
        return await self._PostgresService.get_posts_by_ids(ids=post_UUIDS)
            
    async def get_followed_posts(self, user: User) -> List[Post]:
        return await self._PostgresService.get_followed_posts(user=user)
        