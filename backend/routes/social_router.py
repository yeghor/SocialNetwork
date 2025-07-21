from fastapi import APIRouter, Depends, Body, Query
from pydantic_schemas.pydantic_schemas_auth import UserProfileSchema
from databases_manager.postgres_manager.database_utils import get_session_depends, refresh_model
from databases_manager.main_managers.main_manager_creator_abs import MainServiceContextManager
from databases_manager.main_managers.social_manager import MainServiceSocial
from authorization.authorization import authrorize_request_depends
from pydantic_schemas.pydantic_schemas_social import (
    PostLiteSchema,
    PostSchema,
    UserSchema,
    UserLiteSchema,
    PostDataSchema
)
from databases_manager.postgres_manager.models import User
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Annotated, List

social = APIRouter()

@social.get("/get_related_to_history_posts/")
async def get_related_to_history_posts(
    user_: User = Depends(authrorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    ) -> List[PostLiteSchema]:
    user = await refresh_model(session=session, model_object=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(MainServiceType=MainServiceSocial, postgres_session=session) as social:
        return await social.get_related_posts(user=user)

@social.get("/get_followed_posts/")
async def get_followed_posts(
    user_: User = Depends(authrorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
    ) -> List[PostLiteSchema]:
    user = await refresh_model(session=session, model_object=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(MainServiceType=MainServiceSocial, postgres_session=session) as social:
        return await social.get_followed_posts(user=user)

@social.get("/search_posts/")
async def search_posts(
    user_: User = Depends(authrorize_request_depends),
    prompt: str = Annotated[str, Query(..., max_length=4000)],
    session: AsyncSession = Depends(get_session_depends)
    ) -> List[PostLiteSchema]:
    async with await MainServiceContextManager[MainServiceSocial].create(MainServiceType=MainServiceSocial, postgres_session=session) as social:
        return await social.search_posts(prompt=prompt)

@social.get("/search_users/")
async def search_users(
    user_: User = Depends(authrorize_request_depends),
    prompt: str = Annotated[str, Query(...,)],
    session = Depends(get_session_depends)
    ) -> List[UserLiteSchema]:
    async with await MainServiceContextManager[MainServiceSocial].create(MainServiceType=MainServiceSocial, postgres_session=session) as social:
        return await social.search_users(prompt=prompt)


@social.post("/make_post/")
async def make_post(
    user_: User = Depends(authrorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    post_data: PostDataSchema = Body(...)
    ) -> PostSchema:
    user = await refresh_model(session=session, model_object=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(MainServiceType=MainServiceSocial, postgres_session=session) as social:
        return await social.construct_and_flush_post(data=post_data, user=user)


@social.patch("/change_post/")
async def change_post():
    pass

@social.delete("/delete_post/")
async def delete_post(
    user_: User = Depends(authrorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    post_id: str = Query(...)
) -> None:
    user = await refresh_model(session=session, model_object=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(MainServiceType=MainServiceSocial, postgres_session=session) as social:
        await social.delete_post(post_id=post_id, user=user)

@social.post("/like_post/")
async def like_post(
    user_: User = Depends(authrorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    post_id: str = Query(...)
):
    user = await refresh_model(session=session, model_object=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(MainServiceType=MainServiceSocial, postgres_session=session) as social:
        await social.like_post(post_id=post_id, user=user)

@social.post("/make_replie")
async def make_replie():
    pass


@social.post("/follow")
async def follow():
    pass

@social.post("/unfollow")
async def unfollow():
    pass

@social.patch("/change_password")
async def change_password() -> UserProfileSchema:
    pass

@social.patch("/change_username")
async def change_username() -> UserProfileSchema:
    pass

@social.post("/get_user_profile")
async def get_user_profile() -> UserProfileSchema:
    pass

@social.delete("/delete_user_account")
async def delete_user_account() -> None:
    pass