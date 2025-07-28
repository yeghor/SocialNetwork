from fastapi import HTTPException

from databases_manager.main_managers.main_manager_creator_abs import MainServiceBase
from databases_manager.postgres_manager.models import *
from post_popularity_rate_task.popularity_rate import POST_ACTIONS

from dotenv import load_dotenv
from os import getenv
from typing import List, TypeVar, Type, Tuple
from uuid import UUID
from pydantic_schemas.pydantic_schemas_social import (
    PostSchema,
    PostDataSchemaID,
    MakePostDataSchema,
    PostLiteShortSchema,
    UserLiteSchema,
    UserSchema
)

class NotImplementedError(Exception):
    pass

load_dotenv()

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
        post_ids = await self._ChromaService.get_n_related_posts_ids(user=user)
        
        if not post_ids:
            return await self.get_fresh_feed()

        return await self._PostgresService.get_entries_by_ids(ids=post_ids, ModelType=Post)
        
    async def get_fresh_feed(self) -> List[Post]:
        return await self._PostgresService.get_fresh_posts()

    async def get_followed_posts(self, user: User) -> List[Post]:
        return await self._PostgresService.get_followed_posts(user=user)
    
    async def search_posts(self, prompt: str, user: User) -> List[PostLiteShortSchema | None]:
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
    
    async def search_users(self, prompt: str,  request_user: User) -> List[UserLiteSchema]:
        users = await self._PostgresService.get_users_by_username(prompt=prompt)
        filtered_users = [UserLiteSchema.model_validate(user, from_attributes=True) for user in users if user.user_id != request_user.user_id]
        return filtered_users

    
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
        raise NotImplementedError("Not implemented yet!")
    
    async def delete_post(self, post_id: str, user: User) -> None:
        post = await self._PostgresService.get_entry_by_id(id_=post_id, ModelType=Post)

        self.check_post_user_id(post=post, user=user)

        await self._PostgresService.delete_posts_by_id(ids=[post.post_id])

    async def like_post_action(self, post_id: str, user: User, like: bool = True) -> None:
        """Set like to True to leave like. To remove like - set to False"""

        post = await self._PostgresService.get_entry_by_id(id_=post_id, ModelType=Post)

        if like:
            if user in post.liked_by:
                raise HTTPException(status_code=400, detail="You have already liked this post")
            post.popularity_rate += POST_ACTIONS["like"]
            post.liked_by.append(user)
        else:
            if user not in post.liked_by:
                raise HTTPException(status_code=400, detail="You haven't liked this post yet")
            post.popularity_rate -= POST_ACTIONS["like"]
            await self._PostgresService.make_post_action()
            post.liked_by.remove(user)
            


    async def remove_post_like(self, post_id: str, user: User) -> None:
        post = await self._PostgresService.get_entry_by_id(id_=post_id, ModelType=Post)

        if not user in post.liked_by:
            raise HTTPException(status_code=400, detail="You are not liked this post yet")

        post.liked_by.remove(user)

    async def change_post(self, post_data: PostDataSchemaID, user: User, post_id: str) -> PostSchema:
        post = await self._PostgresService.get_entry_by_id(id_=post_id, ModelType=Post)

        self.check_post_user_id(post=post, user=user)
        
        updated_post = await self._PostgresService.update_post_fields(post_data=post_data, post_id=post_id, return_updated_post = True)
        await self._ChromaService.add_posts_data(posts=[updated_post])
        return PostSchema.model_validate(updated_post, from_attributes=True)

    async def friendship_action(self, user: User, other_user_id: str, follow: bool) -> None:
        """To follow user - set follow to True. To unfollow - False"""
        other_user = await self._PostgresService.get_entry_by_id(id_=other_user_id, ModelType=User)
        
        # Getting fresh user. Because merged Model often lose it's relationships loads
        fresh_user = await self._PostgresService.get_entry_by_id(id_=user.user_id, ModelType=User)

        if follow:
            if other_user in fresh_user.followed:
                raise HTTPException(status_code=400, detail="You are already following this user")
            fresh_user.followed.append(other_user)
        elif not follow:
            if other_user not in fresh_user.followed:
                raise HTTPException(status_code=400, detail="You are not following this user")
            fresh_user.followed.remove(other_user)
    
    # FIX THIS!!!!
    async def get_user_profile(self, request_user: User, other_user_id: str) -> UserSchema:
        # Getting request_user to add feature that doesn't allow see profile of user if you're not in his followers list

        print(request_user.user_id)

        # Just to reuse this method :)
        if request_user.user_id == other_user_id:
            other_user = await self._PostgresService.get_entry_by_id(id_=other_user_id, ModelType=User)
        else:
            other_user = await self._PostgresService.get_entry_by_id(id_=other_user_id, ModelType=User)

        return UserSchema.model_validate(other_user, from_attributes=True)
    
    async def load_post(user: User, post_id: str) -> PostSchema:
        pass