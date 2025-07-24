from fastapi import HTTPException

from databases_manager.main_managers.main_manager_creator_abs import MainServiceBase
from databases_manager.postgres_manager.models import *

from dotenv import load_dotenv
from os import getenv
from typing import List, TypeVar, Type, Tuple
from uuid import UUID
from pydantic_schemas.pydantic_schemas_social import (
    PostSchema,
    PostDataSchemaID,
    MakePostDataSchema,
    PostLiteShortSchema
)

load_dotenv()

DATETIME_BASE_FORMAT = getenv("DATETIME_BASE_FORMAT")

T = TypeVar("T", bound=Base)


class MainServiceSocial(MainServiceBase):
    @staticmethod
    def check_post_user_id(post: Post, user: User) -> None:
        """If ids don't match - raises HTTPException 401"""
        if post.owner_id != user.user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")

    async def sync_data(self) -> None:
        posts = await self._PostgresService.get_all_from_model(ModelType=Post)
        await self._ChromaService.add_posts_data(posts=posts)

    async def get_all_from_specific_model(self, ModelType: Type[T]) -> List[T | None]:
        return await self._PostgresService.get_all_from_model(ModelType=ModelType)

    async def get_related_posts(self, user: User) -> List[Post | None]:
        """
        Returns related posts to provided User table object view history
        """
        post_UUIDS = await self._ChromaService.get_n_related_posts_ids(user=user)
        print(post_UUIDS)
        
        if not post_UUIDS:
            # return await self.get_fresh_feed()
            return []

        return await self._PostgresService.get_entries_by_ids(ids=post_UUIDS, ModelType=Post)
        
    async def get_fresh_feen():
        pass

    async def get_followed_posts(self, user: User) -> List[Post]:
        return await self._PostgresService.get_followed_posts(user=user)
    
    async def search_posts(self, prompt: str) -> List[PostLiteShortSchema | None]:
        """
        Search posts that similar with meaning with prompt
        """
        posts_UUIDS = await self._ChromaService.search_posts_by_prompt(prompt=prompt)
        print(posts_UUIDS)
        posts = await self._PostgresService.get_entries_by_ids(ids=posts_UUIDS, ModelType=Post)
        print(posts)
        model_validated_posts = []

        for post in posts:
            model_validated_posts.append(PostLiteShortSchema.model_validate(post, from_attributes=True))

        return model_validated_posts
    
    async def search_users(self, prompt: str) -> List[User | None]:
        return await self._PostgresService.get_users_by_username(prompt=prompt)
    
    async def construct_and_flush_post(self, data: MakePostDataSchema, user: User) -> PostSchema:
        if data.parent_post_id:
            if not await self._PostgresService.get_entry_by_id(id_=data.parent_post_id):
                raise HTTPException(status_code=400, detail="Youre replying to post that dosen't exist")

        post = Post(
            post_id=str(uuid4()),
            owner_id=user.user_id,
            parent_post_id=data.parent_post_id,
            title=data.title,
            text=data.text,
            image_path=None, # TODO: implement image uploads
            is_reply=bool(data.parent_post_id)
        )

        await self._PostgresService.insert_models_and_flush(post)
        await self._PostgresService.refresh_model(post)

        await self._ChromaService.add_posts_data(posts=[post])

        return PostSchema.model_validate(post, from_attributes=True)

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

    async def construct_and_flush_view(self, post: Post, user: User) -> None:
        """Calling this method when user click on post \n Data must be validated!"""
        raise Exception("Is not implemented yet!")
    
    async def delete_post(self, post_id: str | UUID, user: User, show_replies: bool) -> None:
        post = await self._PostgresService.get_entry_by_id(id_=list(post_id), ModelType=Post)

        self.check_post_user_id(post=post, user=user)
        
        await self._PostgresService.delete_posts_by_id()

    async def like_post(self, post_id: str | UUID, user: User) -> None:
        post = await self._PostgresService.get_entry_by_id(id_=post_id, ModelType=Post)

        if user in post.liked_by:
            raise HTTPException(status_code=400, detail="You are already liekd this post")

        post.liked_by.append(user)

    async def remove_post_like(self, post_id: str | UUID, user: User) -> None:
        post = await self._PostgresService.get_entry_by_id(id_=list(post_id), ModelType=Post)

        if not user in post.liked_by:
            raise HTTPException(status_code=400, detail="You are not liked this post yet")

        post.liked_by.remove(user)

    async def change_post(self, post_data: PostDataSchemaID, user: User) -> None:
        post = await self._PostgresService.get_entry_by_id(id_=post_data.post_id, ModelType=Post)

        self.check_post_user_id(post=post, user=user)
        
        await self._PostgresService.update_post_fields(post_data=post_data, return_updated_post = False)

    async def friendship_action(self, user: User, other_user_id: str | UUID, follow: bool):
        if not isinstance(follow, bool):
            raise TypeError("Uknown follow action")
        """To follow user - set follow to True. To unfollow - False"""
        other_user = await self._PostgresService.get_entry_by_id(id_=other_user_id, ModelType=User)

        if follow:
            if other_user in user.followed:
                raise HTTPException(status_code=400, detail="You are already following this user")
            user.followed.append(other_user)
        elif not follow:
            if other_user not in user.followed:
                raise HTTPException(status_code=400, detail="You are not following this user")
            user.followed.remove(other_user)
    
