from services.core_services import MainServiceBase
from services.postgres_service.models import *
from post_popularity_rate_task.popularity_rate import POST_ACTIONS
from mix_posts_consts import *

from dotenv import load_dotenv
from os import getenv
from typing import List, TypeVar, Type, Literal, Iterable, NamedTuple, Union
from pydantic_schemas.pydantic_schemas_social import (
    PostBaseShort,
    PostSchema,
    PostDataSchemaID,
    MakePostDataSchema,
    PostLiteSchema,
    UserLiteSchema,
    UserSchema,
    UserShortSchema,
    PostBase
)

from exceptions.exceptions_handler import web_exceptions_raiser
from exceptions.custom_exceptions import *


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

REPLY_COST_DEVALUATION = float(getenv("REPLY_COST_DEVALUATION", "0.5"))
MAX_REPLIES_THAT_GIVE_POPULARITY_RATE = int(getenv("MAX_REPLIES_THAT_GIVE_POPULARITY_RATE", "3"))

BASE_PAGINATION = int(getenv("BASE_PAGINATION"))
DIVIDE_BASE_PAG_BY = int(getenv("DIVIDE_BASE_PAG_BY"))
SMALL_PAGINATION = int(getenv("SMALL_PAGINATION"))

T = TypeVar("T", bound=Base)

class IdsPostTuple(NamedTuple):
    ids: List[str]
    posts: List[Post]


class MainServiceSocial(MainServiceBase):
    @staticmethod
    def change_post_rate(post: Post, action_type: ActionType | None, add: bool,  cost: int | None = None) -> None:
        """Set add to True to add rate, False to subtrack \n If you want to increase rate by specific rate - provide cost"""
        if not cost:
            cost = POST_ACTIONS[action_type.value]

        if add: post.popularity_rate += cost
        else: post.popularity_rate -= cost

    @staticmethod
    def combine_lists(*lists: Iterable) -> List:
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
            raise Unauthorized(detail=f"SocialService: User: {user.user_id} tried to access post: {post.post_id}", client_safe_detail="You are not owner of this post!")

    async def _get_ids_by_query_type(self, page: int, user: User, n: int, id_type: Literal["followed", "fresh"], return_posts_too: bool = False, exclude_ids: List[str] = []) -> Union[List[str], NamedTuple]:
        if id_type == "fresh": posts = await self._PostgresService.get_fresh_posts(user=user, exclude_ids=exclude_ids, n=n, page=page)
        elif id_type == "followed": posts = await self._PostgresService.get_followed_posts(user=user, exclude_ids=exclude_ids, n=n, page=page)

        ids = [post.post_id for post in posts]

        if return_posts_too: return (ids, posts)
        else: return ids
        
    async def _construct_and_flush_action(self, action_type: ActionType, user: User, post: Post = None) -> None:
        """Protected method. Do NOT call this method outside the class"""
        actions = await self._PostgresService.get_actions(user_id=user.user_id, post_id=post.post_id, action_type=action_type)
        cost = POST_ACTIONS[action_type.value]

        if actions:
            if action_type == ActionType.view:
                if not await self._RedisService.check_view_timeout(id_=post.post_id, user_id=user.user_id):
                    return
            elif action_type == ActionType.reply:
                if len(actions) < MAX_REPLIES_THAT_GIVE_POPULARITY_RATE:
                    cost = POST_ACTIONS[action_type.value]
                    for _ in range(len(actions)): cost *= REPLY_COST_DEVALUATION
                else: cost = 0
            else:
                raise InvalidAction(detail=f"SocialService: User: {user.user_id} tried to give already giveт action: {action_type.value} to post: {post.post_id} that does not exists.", client_safe_detail="This action is already given to this post.")

        if action_type == ActionType.view:
            await self._RedisService.add_view(user_id=user.user_id, id_=post.post_id)

        self.change_post_rate(post=post, action_type=action_type, cost=cost, add=True)

        action = PostActions(
            action_id=str(uuid4()),
            owner_id=user.user_id,
            post_id=post.post_id,
            action=action_type,
        )
        await self._PostgresService.insert_models_and_flush(action)

    @web_exceptions_raiser
    async def sync_postgres_chroma_DEV_METHOD(self) -> None:
        # TEMPORARY!
        await self._ChromaService.drop_all()
        posts = await self._PostgresService.get_all_from_model(ModelType=Post)
        await self._ChromaService.add_posts_data(posts=posts)

    @web_exceptions_raiser
    async def _get_all_from_specific_model(self, ModelType: Type[T]) -> List[T]:
        return await self._PostgresService.get_all_from_model(ModelType=ModelType)

    @web_exceptions_raiser
    async def get_feed(self, user: User, page: int) -> List[PostLiteSchema]:
        """`
        Returns related posts to provided User table object view history \n
        It mixes history rated with most popular posts, and newest ones.
        """

        # TODO: KISS THIS MOTHERFUCKER

        EACH_SOURCE_PAGINATION = int(BASE_PAGINATION / DIVIDE_BASE_PAG_BY)


        views_history = await self._PostgresService.get_user_actions(user_id=user.user_id, action_type=ActionType.view, n_most_fresh=HISTORY_POSTS_TO_TAKE_INTO_RELATED, return_posts=True)
        liked_history = await self._PostgresService.get_user_actions(user_id=user.user_id, action_type=ActionType.like, n_most_fresh=LIKED_POSTS_TO_TAKE_INTO_RELATED, return_posts=True)
        history_posts_relation = views_history + liked_history



        # History related mix
        if len(views_history) > MINIMUM_USER_HISTORY_LENGTH:
            related_ids = await self._ChromaService.get_n_related_posts_ids(user=user, page=page, post_relation=history_posts_relation, pagination=EACH_SOURCE_PAGINATION)

            # Following mix
            followed_ids =  await self._get_ids_by_query_type(exclude_ids=related_ids, user=user, page=page, n=EACH_SOURCE_PAGINATION, id_type="followed")
            if not followed_ids:
                followed_ids = await self._get_ids_by_query_type(exclude_ids=related_ids, user=user, page=page, n=EACH_SOURCE_PAGINATION, id_type="fresh")

            unrelevant_ids = await self._get_ids_by_query_type(exclude_ids=followed_ids + related_ids, user=user, page=page, n=EACH_SOURCE_PAGINATION, id_type="fresh")
            
        else:
            related_ids = await self._get_ids_by_query_type(page=page, user=user, n=EACH_SOURCE_PAGINATION, id_type="fresh")

            # Following mix
            followed_ids =  await self._get_ids_by_query_type(exclude_ids=related_ids, user=user, page=page, n=EACH_SOURCE_PAGINATION, id_type="followed")
            if not followed_ids:
                followed_ids = await self._get_ids_by_query_type(exclude_ids=related_ids, user=user, page=page+1, n=EACH_SOURCE_PAGINATION, id_type="fresh")
                unrelevant_ids = await self._get_ids_by_query_type(exclude_ids=followed_ids + related_ids, user=user, page=page+2, n=EACH_SOURCE_PAGINATION, id_type="fresh")
            else:
                unrelevant_ids = await self._get_ids_by_query_type(exclude_ids=followed_ids + related_ids, user=user, page=page+1, n=EACH_SOURCE_PAGINATION, id_type="fresh")


        all_ids = self.combine_lists(related_ids, followed_ids, unrelevant_ids)


        posts = await self._PostgresService.get_entries_by_ids(ids=all_ids, ModelType=Post)
        posts = self._shuffle_posts(posts=posts)

        return [
            PostLiteSchema(
                post_id=post.post_id,
                title=post.title,
                published=post.published,
                is_reply=post.is_reply,
                owner=UserShortSchema.model_validate(post.owner, from_attributes=True),
                pictures_urls= await self._ImageStorage.get_post_image_urls(images_names=[post_image.image_name for post_image in post.images]),
                parent_post=post.parent_post
            ) for post in posts
            ]

    @web_exceptions_raiser
    async def get_followed_posts(self, user: User, page: int) -> List[PostLiteSchema]:        
        post_ids, posts = await self._get_ids_by_query_type(page=page, n=BASE_PAGINATION, user=user, id_type="followed", return_posts_too=True)

        posts = self._shuffle_posts(posts=posts)

        return [
            PostLiteSchema(
                post_id=post.post_id,
                title=post.title,
                published=post.published,
                is_reply=post.is_reply,
                owner=post.owner,
                pictures_urls= await self._ImageStorage.get_post_image_urls(images_names=[post_image.image_name for post_image in post.images]),
                parent_post=post.parent_post
            ) for post in posts
            ]
    
    @web_exceptions_raiser
    async def search_posts(self, prompt: str, user: User, page: int) -> List[PostLiteSchema]:
        """
        Search posts that similar with meaning to prompt
        """

        post_ids = await self._ChromaService.search_posts_by_prompt(prompt=prompt, page=page, n=BASE_PAGINATION)
        posts = await self._PostgresService.get_entries_by_ids(ids=post_ids, ModelType=Post)

        return [
            PostLiteSchema(
                post_id=post.post_id,
                title=post.title,
                published=post.published,
                is_reply=post.is_reply,
                owner=UserShortSchema.model_validate(post.owner, from_attributes=True),
                pictures_urls= await self._ImageStorage.get_post_image_urls(images_names=[post_image.image_name for post_image in post.images]),
                parent_post=post.parent_post
            ) for post in posts
            ]

    # @web_exceptions_raiser
    async def search_users(self, prompt: str,  request_user: User, page: int) -> List[UserLiteSchema]:
        users = await self._PostgresService.get_users_by_username(prompt=prompt, page=page, n=BASE_PAGINATION)
        return [UserLiteSchema.model_validate(user, from_attributes=True) for user in users if user.user_id != request_user.user_id]

    @web_exceptions_raiser  
    async def make_post(self, data: MakePostDataSchema, user: User) -> None:
        if data.parent_post_id:
            if not await self._PostgresService.get_entry_by_id(id_=data.parent_post_id, ModelType=Post):
                raise InvalidAction(detail=f"SocialService: User: {user.user_id} tried to reply to post: {data.parent_post_id} that does not exists.", client_safe_detail="Post that you are replying does not exist.")

        post = Post(
            post_id=str(uuid4()),
            owner_id=user.user_id,
            parent_post_id=data.parent_post_id,
            title=data.title,
            text=data.text,
            is_reply=bool(data.parent_post_id)
        )

        await self._PostgresService.insert_models_and_flush(post)
        await self._PostgresService.refresh_model(post)
        await self._ChromaService.add_posts_data(posts=[post])

    @web_exceptions_raiser
    async def remove_action(self, user: User, post: Post, action_type: ActionType) -> None:
        potential_action = await self._PostgresService.get_actions(user_id=user.user_id, post_id=post.post_id, action_type=action_type)
        if not potential_action:
            raise InvalidAction(detail=f"SocialService: User: {user.user_id} tried to reply to post: {post.post_id} that does not exists.")
        
        await self._PostgresService.delete_models_and_flush(potential_action)
        self.change_post_rate(post=post, action_type=action_type, add=False)
    
    @web_exceptions_raiser
    async def delete_post(self, post_id: str, user: User) -> None:
        post = await self._PostgresService.get_entry_by_id(id_=post_id, ModelType=Post)

        if not post:
            raise ResourceNotFound(detail=f"SocialService: User: {user.user_id} tried to delete post: {post_id} that does not exist.", client_safe_detail="Post that you trying to delete does not exist.")

        self.check_post_user_id(post=post, user=user)

        await self._PostgresService.delete_post_by_id(id_=post.post_id)
        await self._ImageStorage.delete_post_images(base_name=post.post_id)
        await self._ChromaService.delete_by_ids(ids=[post.post_id])

    @web_exceptions_raiser
    async def like_post_action(self, post_id: str, user: User, like: bool = True) -> None:
        """Set 'like' param to True to leave like. To remove like - set to False"""
        post = await self._PostgresService.get_entry_by_id(id_=post_id, ModelType=Post)
        if like:
            await self._construct_and_flush_action(action_type=ActionType.like,post=post, user=user)
        else:
            await self.remove_action(user=user, post=post, action_type=ActionType.like)

    @web_exceptions_raiser
    async def change_post(self, post_data: PostDataSchemaID, user: User, post_id: str) -> PostSchema:
        post = await self._PostgresService.get_entry_by_id(id_=post_id, ModelType=Post)

        if not post:
            raise ResourceNotFound(detail=f"SocialService: User: {user.user_id} tried to change post: {post_id} that does not exist.", client_safe_detail="Post that you trying to change does not exist.")

        self.check_post_user_id(post=post, user=user)
        
        updated_post = await self._PostgresService.update_post_fields(post_data=post_data, post_id=post_id, return_updated_post = True)
        await self._ChromaService.add_posts_data(posts=[updated_post])

        return PostSchema.model_validate(updated_post, from_attributes=True)

    @web_exceptions_raiser
    async def friendship_action(self, user: User, other_user_id: str, follow: bool) -> None:
        """To follow user - set follow to True. To unfollow - False"""

        if user.user_id == other_user_id:
            raise InvalidAction(detail=f"SocialService: User: {user.user_id} tried to follow himself.", client_safe_detail="You can't follow yourself.")

        other_user = await self._PostgresService.get_entry_by_id(id_=other_user_id, ModelType=User)
        
        # Getting fresh user. Because merged Model often lose it's relationships loads
        fresh_user = await self._PostgresService.get_entry_by_id(id_=user.user_id, ModelType=User)

        if follow:
            if other_user in fresh_user.followed:
                raise InvalidAction(detail=f"SocialService: User: {user.user_id} tried to follow user: {other_user.user_id} already following him", client_safe_detail="You are already following this user. You can't follow him")
            fresh_user.followed.append(other_user)
        elif not follow:
            if other_user not in fresh_user.followed:
                raise InvalidAction(detail=f"SocialService: User: {user.user_id} tried to unfollow user: {other_user.user_id} not following him", client_safe_detail="You are not following this user. You can't unfollow him")
            fresh_user.followed.remove(other_user)
    
    @web_exceptions_raiser
    async def get_user_profile(self, user_id: str, other_user_id: str) -> UserSchema:
        other_user = await self._PostgresService.get_entry_by_id(id_=other_user_id, ModelType=User)

        if not other_user: 
            raise ResourceNotFound(detail=f"User: {user_id} tried to get user: {other_user_id} profile that does not exist.", client_safe_detail="User profile that you trying to get does not exist.")

        avatar_token = await self._ImageStorage.get_user_avatar_url(user_id=other_user.user_id)

        return UserSchema(
            user_id=other_user.user_id,
            username=other_user.username,
            followers=[UserShortSchema.model_validate(follower, from_attributes=True) for follower in other_user.followers],
            followed=[UserShortSchema.model_validate(followed, from_attributes=True) for followed in other_user.followed],
            avatar_url=avatar_token
        )
    
    @web_exceptions_raiser
    async def get_users_posts(self, user_id: str, page: int) -> PostLiteSchema:
        posts = await self._PostgresService.get_user_posts(user_id=user_id, page=page, n=SMALL_PAGINATION)

        return [
            PostLiteSchema(
                post_id=post.post_id,
                title=post.title,
                published=post.published,
                is_reply=post.is_reply,
                owner=post.owner,
                pictures_urls= await self._ImageStorage.get_post_image_urls(images_names=[post_image.image_name for post_image in post.images]),
                parent_post=post.parent_post
            ) for post in posts
            ]
    
    @web_exceptions_raiser
    async def get_my_profile(self, user: User) -> UserSchema:
        """To use this method you firstly need to get User instance by Bearer token"""

        # To prever SQLalechemy missing greenlet_spawn error. Cause merged model loses relationships
        user = await self._PostgresService.get_entry_by_id(id_=user.user_id, ModelType=User)

        avatar_token = await self._ImageStorage.get_user_avatar_url(user_id=user.user_id)

        return UserSchema(
            user_id=user.user_id,
            username=user.username,
            followers=user.followers,
            followed=user.followed,
            posts=user.posts,
            avatar_url=avatar_token
        )

    @web_exceptions_raiser
    async def load_post(self, user: User, post_id: str) -> PostSchema:
        post = await self._PostgresService.get_entry_by_id(id_=post_id, ModelType=Post)

        if not post:
            raise ResourceNotFound(detail=f"SocialService: User: {user.user_id} tried to load post: {post_id} that does not exist.", client_safe_detail="This post does not exist.")

        if post.parent_post: parent_post = PostBase.model_validate(post.parent_post, from_attributes=True)
        else: parent_post = None

        await self._construct_and_flush_action(action_type=ActionType.view, post=post, user=user)

        await self._PostgresService.refresh_model(model_obj=post)

        post_likes = await self._PostgresService.get_actions(user_id=user.user_id, post_id=post.post_id, action_type=ActionType.like)
        post_views = await self._PostgresService.get_actions(user_id=user.user_id, post_id=post.post_id, action_type=ActionType.view)

        filenames = [filename.image_name for filename in post.images]
        images_temp_urls = await self._ImageStorage.get_post_image_urls(image_names=filenames)

        return PostSchema(
            post_id=post.post_id,
            title=post.title,
            text=post.text,
            published=post.published,
            owner=UserShortSchema.model_validate(post.owner, from_attributes=True),
            likes=len(post_likes),
            views=len(post_views),
            parent_post=parent_post,
            last_updated=post.last_updated,
            pictures_urls=images_temp_urls,
            is_reply=post.is_reply
        )

    @web_exceptions_raiser
    async def load_replies(self, post_id: str, page: int) -> List[PostBase]:
        replies = await self._PostgresService.get_post_replies(post_id=post_id, page=page, n=SMALL_PAGINATION)
        return [PostBase.model_validate(reply, from_attributes=True) for reply in replies]        
    
    @web_exceptions_raiser
    async def get_user_posts(self, user_id: str, page: int) -> List[PostLiteSchema]:
        user_posts = await self._PostgresService.get_user_posts(user_id=user_id, page=page, n=SMALL_PAGINATION)

        return [PostLiteSchema(
            post_id=post.post_id,
            title=post.title,
            published=post.published,
            is_reply=post.is_reply,
            pictures_urls=[await self._ImageStorage.get_post_image_urls(images_names=image.image_name) for image in post.images],
            owner=UserShortSchema.model_validate(post.owner, from_attributes=True),
            parent_post=PostBase.model_validate(post.parent_post, from_attributes=True) if post.parent_post else None
        ) for post in user_posts]