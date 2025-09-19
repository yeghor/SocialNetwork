import re
from fastapi import APIRouter, Depends, Body, Query, HTTPException
from posthog import page
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

from exceptions.exceptions_handler import endpoint_exception_handler

from .query_utils import page_validator, query_prompt_required

social = APIRouter()

load_dotenv()
QUERY_PARAM_MAX_L = int(getenv("QUERY_PARAM_MAX_L"))


@social.get("/posts/feed/{page}")
@endpoint_exception_handler
async def get_feed(
    page: int = Depends(page_validator),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    ) -> List[PostLiteSchema]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.get_feed(user=user, page=page)

@social.get("/posts/following")
@endpoint_exception_handler
async def get_followed_posts(
    page: int = Depends(page_validator),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
    ) -> List[PostLiteSchema]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.get_followed_posts(user=user, page=page)

@social.get("/search/posts")
# @endpoint_exception_handler
async def search_posts(
    page: int = Depends(page_validator),
    prompt: str = Depends(query_prompt_required),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
    ) -> List[PostLiteSchema]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.search_posts(prompt=prompt, user=user, page=page)

@social.get("/search/users/{page}")
# @endpoint_exception_handler
async def search_users(
    prompt: str = Depends(query_prompt_required),
    page: str = Depends(page_validator),
    user_: User = Depends(authorize_request_depends),
    session = Depends(get_session_depends)
    ) -> List[UserLiteSchema]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.search_users(prompt=prompt, request_user=user, page=page)

@social.post("/posts")
@endpoint_exception_handler
async def make_post(
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    post_data: MakePostDataSchema = Body(...)
    ) -> None:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        await social.make_post(data=post_data, user=user)

@social.get("/posts/{post_id}")
@endpoint_exception_handler
async def load_post(
    post_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> PostSchema:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.load_post(user=user, post_id=post_id)

@social.get("/posts/{post_id}/comments")
@endpoint_exception_handler
async def load_comments(
    post_id: str,
    page: int = Depends(page_validator),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> List[PostBase]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.load_replies(post_id=post_id, user_id=user.user_id, page=page)

@social.patch("/posts/{post_id}")
@endpoint_exception_handler
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
@endpoint_exception_handler
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
@endpoint_exception_handler
async def like_post(
    post_id: str | None,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
):
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        await social.like_post_action(post_id=post_id, user=user, like=True)

@social.delete("/posts/{post_id}/like")
@endpoint_exception_handler
async def unlike_post(
    post_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> None:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        await social.like_post_action(post_id=post_id, user=user, like=False)

@social.post("/users/{follow_to_id}/follow")
@endpoint_exception_handler
async def follow(
    follow_to_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
) -> None:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        await social.friendship_action(user=user, other_user_id=follow_to_id, follow=True)

@social.delete("/users/{follow_to_id}/follow")
@endpoint_exception_handler
async def unfollow(
    unfollow_from_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
) -> None:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        await social.friendship_action(user=user, other_user_id=unfollow_from_id, follow=False)

@social.get("/users/my-profile")
@endpoint_exception_handler
async def get_my_profile(
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    ) -> UserSchema:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.get_my_profile(user=user)

@social.get("/users/{user_id}")
@endpoint_exception_handler
async def get_user_profile(
    user_id: str | None,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    )-> UserSchema:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.get_user_profile(user_id=user.user_id, other_user_id=user_id)
    
@social.get("/users/{user_id}/posts/{page}")
@endpoint_exception_handler
async def get_users_posts(
    user_id: str,
    page: int = Depends(page_validator),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> List[PostLiteSchema]:
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.get_user_posts(user_id, page)