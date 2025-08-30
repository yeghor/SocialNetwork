from fastapi import APIRouter, Depends, Body, Query, HTTPException
from services.postgres_service.database_utils import *
from services.postgres_service.models import User
from services.core_services import MainServiceContextManager
from services.core_services.main_services.main_social_service import MainServiceSocial
from authorization.authorization_utils import authorize_request_depends
from pydantic_schemas.pydantic_schemas_social import (
    UserLiteSchema,
    PostBase,
    PostLiteSchema,
    PostSchema,
    MakePostDataSchema,
    PostDataSchemaBase,
    UserSchema
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import inspect

from typing import Annotated, List
from dotenv import load_dotenv
from os import getenv

social = APIRouter()

load_dotenv()
QUERY_PARAM_MAX_L = int(getenv("QUERY_PARAM_MAX_L"))

def query_prompt_required(prompt: Annotated[str, Query(..., max_length=QUERY_PARAM_MAX_L)]):
    # Somehow... But Depends() makes prompt Query field required...
    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt can't be empty!")
    return prompt

def query_exclude_required(exclude_viewed: bool = Query(..., description="Exclude viewed post. Set to True if user pressed 'load more' button")):
    if not isinstance(exclude_viewed, bool):
        raise HTTPException(status_code=400, detail="Exclude posts wasn't specified correctly")
    return exclude_viewed

@social.get("/posts/feed")
async def get_feed(
    exclude_viewed: bool = Depends(query_exclude_required),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    ) -> List[PostLiteSchema]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.get_feed(user=user, exclude=exclude_viewed)

@social.get("/posts/following")
async def get_followed_posts(
    exclude_viewed: bool = Depends(query_exclude_required),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
    ) -> List[PostLiteSchema]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.get_followed_posts(user=user, exclude=exclude_viewed)

@social.get("/search/posts")
async def search_posts( # TODO: Exclude self posts
    exclude: bool = Depends(query_exclude_required),
    prompt: str = Depends(query_prompt_required),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
    ) -> List[PostLiteSchema]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.search_posts(prompt=prompt, user=user, exclude=exclude)

@social.get("/search/users")
async def search_users(
    prompt: str = Depends(query_prompt_required),
    user_: User = Depends(authorize_request_depends),
    session = Depends(get_session_depends)
    ) -> List[UserLiteSchema]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        users = await social.search_users(prompt=prompt, request_user=user)
        return users

@social.post("/posts")
async def make_post(
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    post_data: MakePostDataSchema = Body(...)
    ) -> PostSchema:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.make_post(data=post_data, user=user)

@social.get("/posts/{post_id}")
async def load_post(
    post_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> PostSchema:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.load_post(user=user, post_id=post_id)

@social.get("/posts/{post_id}/comments")
async def load_comments(
    post_id: str,
    exclude: bool = Depends(query_exclude_required),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> List[PostBase]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.load_comments(post_id=post_id, user_id=user.user_id, exclude=exclude)

@social.patch("/posts/{post_id}")
async def change_post(
    post_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    post_data: PostDataSchemaBase = Body(...),
) -> PostSchema:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.change_post(post_data=post_data, user=user, post_id=post_id)

@social.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
) -> None:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        print(post_id)
        await social.delete_post(post_id=post_id, user=user)

@social.post("/posts/{post_id}/like")
async def like_post(
    post_id: str | None,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
):
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        await social.like_post_action(post_id=post_id, user=user, like=True)

@social.delete("/posts/{post_id}/like")
async def unlike_post(
    post_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> None:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        await social.like_post_action(post_id=post_id, user=user, like=False)

@social.post("/users/{follow_to_id}/follow")
async def follow(
    follow_to_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
) -> None:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        await social.friendship_action(user=user, other_user_id=follow_to_id, follow=True)

@social.delete("/users/{follow_to_id}/follow")
async def unfollow(
    unfollow_from_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
) -> None:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        await social.friendship_action(user=user, other_user_id=unfollow_from_id, follow=False)

@social.get("/users/my-profile")
async def get_my_profile(
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    ) -> UserSchema:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.get_my_profile(user=user)

@social.get("/users/{user_id}")
async def get_user_profile(
    user_id: str | None,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    )-> UserSchema:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.get_user_profile(user_id=user.user_id, other_user_id=user_id)