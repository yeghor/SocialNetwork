from fastapi import HTTPException

from databases_manager.main_managers.main_manager_creator_abs import MainServiceBase
from databases_manager.postgres_manager.models import *
from post_popularity_rate_task.popularity_rate import POST_ACTIONS
from databases_manager.main_managers.mix_posts import MIX_FOLLOWING, MIX_UNRELEVANT, MIX_HISTORY_POSTS_RELATED

from dotenv import load_dotenv
from os import getenv
from typing import List, TypeVar, Type, Literal, Iterable
from pydantic_schemas.pydantic_schemas_social import (
    PostSchema,
    PostDataSchemaID,
    MakePostDataSchema,
    PostLiteSchema,
    UserLiteSchema,
    UserSchema,
    UserShortSchema,
    PostBase
)

class NotImplementedError(Exception):
    pass

load_dotenv()

HISTORY_POSTS_TO_TAKE_INTO_RELATED = int(getenv("HISTORY_POSTS_TO_TAKE_INTO_RELATED", 30))
REPLY_COST_DEVALUATION = float(getenv("REPLY_COST_DEVALUATION")) # TODO: Devaluate multiple replies cost. To prevent popularity rate abuse
FEED_MAX_POSTS_LOAD = int(getenv("FEED_MAX_POSTS_LOAD"))
MINIMUM_USER_HISTORY_LENGTH = int(getenv("MINIMUM_USER_HISTORY_LENGTH"))

SHUFFLE_BY_RATE = float(getenv("SHUFFLE_BY_RATE", "0.7"))
SHUFFLE_BY_TIMESTAMP = float(getenv("SHUFFLE_BY_TIMESTAMP", "0.3"))

T = TypeVar("T", bound=Base)

class MainServiceSocial(MainServiceBase):
    @staticmethod
    def change_post_rate(post: Post, action_type: ActionType, add: bool) -> None:
        """Set add to True to add tate, False to subtrack"""
        cost = POST_ACTIONS[action_type.value]
        if add: 
            post.popularity_rate += cost
        else:
            post.popularity_rate -= cost

    @staticmethod
    def extend_list(*lists: Iterable) -> List:
        to_return = []
        for lst in lists:
            to_return.extend(lst)
        print(to_return)
        return to_return

    @staticmethod
    def shuffle_posts(posts: List[Post]) -> List[Post]:
        return sorted(posts, key=lambda post: (post.popularity_rate * SHUFFLE_BY_RATE, int(post.published.timestamp()) * SHUFFLE_BY_TIMESTAMP))

    @staticmethod
    def check_post_user_id(post: Post, user: User) -> None:
        """If ids doesn't match - raises HTTPException 401"""
        if post.owner_id != user.user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")

    async def sync_postgres_chroma_DEV_METHOD(self) -> None:
        # TEMPORARY!
        await self._ChromaService.drop_all()
        posts = await self._PostgresService.get_all_from_model(ModelType=Post)
        await self._ChromaService.add_posts_data(posts=posts)

    async def _get_all_from_specific_model(self, ModelType: Type[T]) -> List[T]:
        return await self._PostgresService.get_all_from_model(ModelType=ModelType)

    async def get_feed(self, user: User, exclude: bool) -> List[PostLiteSchema]:
        """
        Returns related posts to provided User table object view history \n
        It mixes history rated with most popular posts, and newest ones.
        Caution! If `exclude` set to True. It means that user clicked on `Load more` button and we need to update Redis exclude ids with fresh loaded. And ensure that we load non repeating posts \n
        """
        exclude_ids = []
        if exclude:
            exclude_ids = await self._RedisService.get_exclude_post_ids(user_id=user.user_id, exclude_type="feed")
        else:
            await self._RedisService.clear_exclude(exclude_type="feed", user_id=user.user_id)

        views_history = await self._PostgresService.get_user_actions(user_id=user.user_id, action_type=ActionType.view, n_most_fresh=HISTORY_POSTS_TO_TAKE_INTO_RELATED, return_posts=True)

        # History related mix
        related_ids = []
        if len(views_history) > MINIMUM_USER_HISTORY_LENGTH:
            related_ids = await self._ChromaService.get_n_related_posts_ids(user=user, exclude_ids=exclude_ids, views_history=views_history)
        
        if not related_ids:
            related_ids = await self._get_ids_by_query_type(exclude_ids=exclude_ids, user=user, n=MIX_HISTORY_POSTS_RELATED, id_type="fresh")

        exclude_ids.extend(related_ids)



        # Following mix
        following_ids =  await self._get_ids_by_query_type(user=user, exclude_ids=exclude_ids, n=MIX_FOLLOWING, id_type="followed")
        if not following_ids:
            following_ids = await self._get_ids_by_query_type(user=user, exclude_ids=exclude_ids, n=MIX_FOLLOWING, id_type="fresh")
        exclude_ids.extend(following_ids)


        # Mix unrelevant
        unrelevant_ids = await self._get_ids_by_query_type(user=user, exclude_ids=exclude_ids, n=MIX_UNRELEVANT, id_type="fresh")


        all_ids = self.extend_list(related_ids, following_ids, unrelevant_ids)

        await self._RedisService.add_exclude_post_ids(post_ids=all_ids, user_id=user.user_id, exclude_type="feed")
        
        posts = await self._PostgresService.get_entries_by_ids(ids=all_ids, ModelType=Post)
        posts = self.shuffle_posts(posts=posts)
        return [PostLiteSchema.model_validate(post, from_attributes=True) for post in posts]
        
    async def _get_ids_by_query_type(self, exclude_ids: List[str], user: User, n: int, id_type: Literal["followed", "fresh"]) -> List[str]:
        posts = []
        if id_type == "fresh": posts = await self._PostgresService.get_fresh_posts(user=user, exclude_ids=exclude_ids, n=n)
        elif id_type == "followed": posts = await self._PostgresService.get_followed_posts(user=user, exclude_ids=exclude_ids, n=n)

        return [post.post_id for post in posts]

    # TODO: Implement post excluding
    async def get_followed_posts(self, user: User) -> List[Post]:
        return await self._PostgresService.get_followed_posts(user=user, n=FEED_MAX_POSTS_LOAD)
    
    async def search_posts(self, prompt: str, user: User, exclude: bool) -> List[PostLiteSchema]:
        """
        Search posts that similar with meaning with prompt
        """

        exclude_ids = []
        if exclude:
            exclude_ids = await self._RedisService.get_exclude_post_ids(user_id=user.user_id, exclude_type="search")
        else:
            await self._RedisService.clear_exclude(exclude_type="search", user_id=user.user_id)
        
        post_ids = await self._ChromaService.search_posts_by_prompt(prompt=prompt, exclude_ids=exclude_ids)
        posts = await self._PostgresService.get_entries_by_ids(ids=post_ids, ModelType=Post)

        await self._RedisService.add_exclude_post_ids(post_ids=post_ids, user_id=user.user_id, exclude_type="search")

        return [PostLiteSchema.model_validate(post, from_attributes=True) for post in posts]

    async def search_users(self, prompt: str,  request_user: User) -> List[UserLiteSchema]:
        users = await self._PostgresService.get_users_by_username(prompt=prompt)
        return [UserLiteSchema.model_validate(user, from_attributes=True) for user in users if user.user_id != request_user.user_id]
        
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

        if post.parent_post:
            parent_post_validated = PostBase.model_validate(post.parent_post, from_attributes=True)
        else:
            parent_post_validated = None

        return PostSchema(
            post_id=post.post_id,
            owner=UserShortSchema.model_validate(user, from_attributes=True),
            title=post.title,
            text=post.text,
            image_path=None, # TODO 
            last_updated=post.last_updated,
            published=post.published,
            parent_post=parent_post_validated,
            replies=[]
        )

    async def _construct_and_flush_action(self, action_type: ActionType, user: User, post: Post = None) -> None:
        """Do NOT call this method outside the class"""

        # if user.user_id == post.owner_id:
        #     # To prevent self popularity abuse
        #     return

        change_rate: bool = True

        if await self._PostgresService.get_actions(user_id=user.user_id, post_id=post.post_id, action_type=action_type):
            if action_type == ActionType.view:
                change_rate = False
                if not await self._RedisService.check_view_timeout(id_=post.post_id, user_id=user.user_id):
                    return
                await self._RedisService.add_view(user_id=user.user_id, id_=post.post_id)
            elif action_type == ActionType.reply:
                # TODO: Reply populatiry rate evaluation
                pass
            else:
                raise HTTPException(status_code=400, detail=f"Action: '{action_type}' is already given on this post")

        if change_rate:
            self.change_post_rate(post=post, action_type=action_type, add=True)

        action = PostActions(
            action_id=str(uuid4()),
            owner_id=user.user_id,
            post_id=post.post_id,
            action=action_type,
        )
        await self._PostgresService.insert_models_and_flush(action)

    async def remove_action(self, user: User, post: Post, action_type: ActionType) -> None:
        potential_action = await self._PostgresService.get_actions(user_id=user.user_id, post_id=post.post_id, action_type=action_type)
        if not potential_action:
            raise HTTPException(status_code=400, detail=f"Action '{action_type} was not given to this post'")
        
        await self._PostgresService.delete_models_and_flush(potential_action)
        self.change_post_rate(post=post, action_type=action_type, add=False)
    

    async def delete_post(self, post_id: str, user: User) -> None:
        post = await self._PostgresService.get_entry_by_id(id_=post_id, ModelType=Post)

        self.check_post_user_id(post=post, user=user)

        await self._PostgresService.delete_post_by_id(id_=post.post_id)
        await self._ChromaService.delete_by_ids(ids=[post.post_id])


    async def like_post_action(self, post_id: str, user: User, like: bool = True) -> None:
        """Set 'like' param to True to leave like. To remove like - set to False"""
        post = await self._PostgresService.get_entry_by_id(id_=post_id, ModelType=Post)
        if like:
            await self._construct_and_flush_action(action_type=ActionType.like,post=post, user=user)
        else:
            await self.remove_action(user=user, post=post, action_type=ActionType.like)


    async def change_post(self, post_data: PostDataSchemaID, user: User, post_id: str) -> PostSchema:
        post = await self._PostgresService.get_entry_by_id(id_=post_id, ModelType=Post)

        if not post:
            raise HTTPException(status_code=400, detail="Post with this id doesn't exist")

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

        # Just to reuse this method
        if request_user.user_id == other_user_id:
            other_user = await self._PostgresService.get_entry_by_id(id_=other_user_id, ModelType=User)
        else:
            other_user = await self._PostgresService.get_entry_by_id(id_=other_user_id, ModelType=User)

        return UserSchema.model_validate(other_user, from_attributes=True)
    
    async def load_post(self, user: User, post_id: str) -> PostSchema:
        post = await self._PostgresService.get_entry_by_id(id_=post_id, ModelType=Post)

        if not post:
            raise HTTPException(status_code=400, detail="Post with this id doesn't exist")

        await self._construct_and_flush_action(action_type=ActionType.view, post=post, user=user)

        liked_by = await self._PostgresService.get_post_action_by_type(post_id=post.post_id, action_type=ActionType.like) 
        viewed_by = await self._PostgresService.get_post_action_by_type(post_id=post.post_id, action_type=ActionType.view) 

        viewed_by_validated = None

        if post.owner_id == user.user_id:
            viewed_by_validated = [UserShortSchema.model_validate(action.owner, from_attributes=True) for action in viewed_by if action]
        liked_by_validated = [UserShortSchema.model_validate(action.owner, from_attributes=True) for action in liked_by if action]

        return PostSchema(
            post_id=post.post_id,
            title=post.title,
            text=post.text,
            image_path=None,
            published=post.published,
            owner=UserShortSchema.model_validate(post.owner, from_attributes=True),
            liked_by=liked_by_validated,
            likes=len(liked_by),
            viewed_by=viewed_by_validated,
            views=len(viewed_by),
            parent_post=post.parent_post,
            replies=post.replies,
            last_updated=post.last_updated
        )