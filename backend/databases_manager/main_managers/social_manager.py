from fastapi import HTTPException

from databases_manager.main_managers.services_creator_abstractions import MainServiceBase
from databases_manager.postgres_manager.models import *
from post_popularity_rate_task.popularity_rate import POST_ACTIONS
from databases_manager.main_managers.mix_posts import MIX_FOLLOWING, MIX_UNRELEVANT, MIX_HISTORY_POSTS_RELATED

from dotenv import load_dotenv
from os import getenv
from typing import List, TypeVar, Type, Literal, Iterable, NamedTuple, Union
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
LIKED_POSTS_TO_TAKE_INTO_RELATED = int(getenv("LIKED_POSTS_TO_TAKE_INTO_RELATED", 10))
REPLY_COST_DEVALUATION = float(getenv("REPLY_COST_DEVALUATION")) # TODO: Devaluate multiple replies cost. To prevent popularity rate abuse
FEED_MAX_POSTS_LOAD = int(getenv("FEED_MAX_POSTS_LOAD"))
MINIMUM_USER_HISTORY_LENGTH = int(getenv("MINIMUM_USER_HISTORY_LENGTH"))

SHUFFLE_BY_RATE = float(getenv("SHUFFLE_BY_RATE", "0.7"))
SHUFFLE_BY_TIMESTAMP = float(getenv("SHUFFLE_BY_TIMESTAMP", "0.3"))

T = TypeVar("T", bound=Base)

class IdsPostTuple(NamedTuple):
    ids: List[str]
    posts: List[Post]


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
    def _shuffle_posts(posts: List[Post]) -> List[Post]:
        return sorted(posts, key=lambda post: (post.popularity_rate * SHUFFLE_BY_RATE, int(post.published.timestamp()) * SHUFFLE_BY_TIMESTAMP), reverse=True)

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
        """`
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
        liked_history = await self._PostgresService.get_user_actions(user_id=user.user_id, action_type=ActionType.like, n_most_fresh=LIKED_POSTS_TO_TAKE_INTO_RELATED, return_posts=True)
        history_posts_relation = views_history + liked_history

        # History related mix
        related_ids = []
        if len(views_history) > MINIMUM_USER_HISTORY_LENGTH:
            related_ids = await self._ChromaService.get_n_related_posts_ids(user=user, exclude_ids=exclude_ids, post_relation=history_posts_relation)
        
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
        posts = self._shuffle_posts(posts=posts)
        return [PostLiteSchema.model_validate(post, from_attributes=True) for post in posts]
        
    async def _get_ids_by_query_type(self, exclude_ids: List[str], user: User, n: int, id_type: Literal["followed", "fresh"], return_posts_too: bool = False) -> Union[List[str], NamedTuple]:
        posts = []
        if id_type == "fresh": posts = await self._PostgresService.get_fresh_posts(user=user, exclude_ids=exclude_ids, n=n)
        elif id_type == "followed": posts = await self._PostgresService.get_followed_posts(user=user, exclude_ids=exclude_ids, n=n)

        ids = [post.post_id for post in posts]

        if return_posts_too: return (ids, posts)
        else: return ids

    async def get_followed_posts(self, user: User, exclude: bool) -> List[PostLiteSchema]:
        exclude_ids = []
        if exclude:
            exclude_ids = await self._RedisService.get_exclude_post_ids(user_id=user.user_id, exclude_type="feed")
        else:
            await self._RedisService.clear_exclude(user_id=user.user_id, exclude_type="feed")
        
        post_ids, posts = await self._get_ids_by_query_type(exclude_ids=exclude_ids, user=user, n=FEED_MAX_POSTS_LOAD, id_type="followed", return_posts_too=True)
        await self._RedisService.add_exclude_post_ids(post_ids=post_ids, user_id=user.user_id, exclude_type="feed")

        posts = self._shuffle_posts(posts=posts)

        return [PostLiteSchema.model_validate(post, from_attributes=True) for post in posts]

    async def search_posts(self, prompt: str, user: User, exclude: bool) -> List[PostLiteSchema]:
        """
        Search posts that similar with meaning with prompt
        """

        if exclude:
            exclude_ids = await self._RedisService.get_exclude_post_ids(user_id=user.user_id, exclude_type="search")
        else:
            exclude_ids = []
            await self._RedisService.clear_exclude(exclude_type="search", user_id=user.user_id)
        
        post_ids = await self._ChromaService.search_posts_by_prompt(prompt=prompt, exclude_ids=exclude_ids)
        posts = await self._PostgresService.get_entries_by_ids(ids=post_ids, ModelType=Post)

        await self._RedisService.add_exclude_post_ids(post_ids=post_ids, user_id=user.user_id, exclude_type="search")

        return [PostLiteSchema.model_validate(post, from_attributes=True) for post in posts]

    async def search_users(self, prompt: str,  request_user: User) -> List[UserLiteSchema]:
        users = await self._PostgresService.get_users_by_username(prompt=prompt)
        return [UserLiteSchema.model_validate(user, from_attributes=True) for user in users if user.user_id != request_user.user_id]
        
    async def make_post(self, data: MakePostDataSchema, user: User) -> PostSchema:
        if data.parent_post_id:
            if not await self._PostgresService.get_entry_by_id(id_=data.parent_post_id, ModelType=Post):
                raise HTTPException(status_code=404, detail="Youre replying to post that dosen't exist")

        post = Post(
            post_id=str(uuid4()),
            owner_id=user.user_id,
            parent_post_id=data.parent_post_id,
            title=data.title,
            text=data.text,
            is_reply=bool(data.parent_post_id)
        )

        await self._PostgresService.insert_models_and_flush(post)

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

    async def construct_and_flush_view(post: Post, user: User) -> None:
        """Calling this method when user click on post \n Data must be validated!"""
        raise Exception("Is not implemented yet!")