from databases_manager.main_managers.main_manager_creator_abs import MainServiceBase
from databases_manager.postgres_manager.models import User, Post, Base

from dotenv import load_dotenv
from os import getenv
from typing import List, TypeVar, Type
from uuid import UUID

load_dotenv()

T = TypeVar("T", bound=Base)

class MainServiceSocial(MainServiceBase):
    async def sync_data(self) -> None:
        posts = await self._PostgresService.get_all_from_model()
        await self._ChromaService.add_posts_data(posts=posts)

    async def get_all_from_specific_model(self, ModelType: Type[T]) -> List[T | None]:
        return await self._PostgresService.get_all_from_model(ModelType=ModelType)

    async def get_related_posts(self, user: User) -> List[Post | None]:
        """
        Returns related posts to provided User table object view history
        """
        post_UUIDS = await self._ChromaService.get_n_related_posts_ids(user=user)
        return await self._PostgresService.get_entries_by_ids(ids=post_UUIDS, ModelType=Post)
            
    async def get_followed_posts(self, user: User) -> List[Post]:
        return await self._PostgresService.get_followed_posts(user=user)
    
    async def search_posts(self, prompt: str) -> List[Post | None]:
        """
        Search posts that similar with meaning with prompt
        """
        posts_UUIDS = await self._ChromaService.search_posts_by_prompt(prompt=prompt)
        return await self._PostgresService.get_entries_by_ids(ids=posts_UUIDS, ModelType=Post)
    
    async def search_users(self, prompt: str) -> List[User | None]:
        return await self._PostgresService.get_users_by_username(prompt=prompt)
    
    # Add pydantic models!
    async def construct_and_flush_post(
            self,
            owner_id: UUID,
            parent_post_id: UUID | str | None,
            title: str,
            text: str,
            likes: int = 0,
            image_path: str | None = None,
            is_reply: bool = False
        ) -> None:
        """Data must be validated!"""
        if is_reply and not parent_post_id or parent_post_id and not is_reply:
            raise ValueError("If post is reply - it must contain parent_post_id, and is_reply setted to true!")

        post = Post(
            owner_id=owner_id,
            parent_post_id=parent_post_id if parent_post_id else None,
            title=title,
            text=text,
            likes=likes,
            image_path=image_path,
            is_reply=is_reply
        )
        await self._PostgresService.insert_models_and_flush(post)

    # Add pydantic models!
    async def construct_and_flush_user(self,
        username: str,
        email: str,
        password_hash: str
        ) -> None:
        """Data must be validated!"""
        user = User(
            username=username,
            email=email,
            password_hash=password_hash
        )
        await self._PostgresService.insert_models_and_flush(user)

    # Add pydantic models!
    async def construct_and_flush_view(post: Post, user: User) -> None:
        """Calling this method when user click on post \n Data must be validated!"""
        raise Exception("Is not implemented yet!")