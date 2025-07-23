from fastapi import APIRouter, Depends, Body, Query
from pydantic_schemas.pydantic_schemas_auth import UserProfileSchema
from databases_manager.postgres_manager.database_utils import get_session_depends, refresh_model
from databases_manager.main_managers.main_manager_creator_abs import MainServiceContextManager
from databases_manager.main_managers.social_manager import MainServiceSocial, create_main_service_refresh_user
from authorization.authorization import authorize_request_depends
from pydantic_schemas.pydantic_schemas_social import (
    PostLiteSchema,
    PostSchema,
    UserSchema,
    UserLiteSchema,
    PostDataSchemaID,
    MakePostDataSchema
)
from databases_manager.postgres_manager.models import User
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Annotated, List

social = APIRouter()

@social.get("/posts/history-related")
async def get_related_to_history_posts(
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    ) -> List[PostLiteSchema]:
    social, user = await create_main_service_refresh_user(MainService=MainServiceSocial, postgres_session=session, user=user_)
    async with social as s:
        return await s.get_related_posts(user=user)

@social.get("/posts/following")
async def get_followed_posts(
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
    ) -> List[PostLiteSchema]:
    social, user = await create_main_service_refresh_user(MainService=MainServiceSocial, postgres_session=session, user=user_)
    async with social:
        return await social.get_followed_posts(user=user)

@social.get("search/posts")
async def search_posts(
    user_: User = Depends(authorize_request_depends),
    prompt: str = Annotated[str, Query(..., max_length=4000)],
    session: AsyncSession = Depends(get_session_depends)
    ) -> List[PostLiteSchema]:
    social = await create_main_service_refresh_user(MainService=MainServiceSocial, postgres_session=session)
    async with social:
        return await social.search_posts(prompt=prompt)

@social.get("search/users")
async def search_users(
    user_: User = Depends(authorize_request_depends),
    prompt: str = Annotated[str, Query(...,)],
    session = Depends(get_session_depends)
    ) -> List[UserLiteSchema]:
    social = await create_main_service_refresh_user(MainService=MainServiceSocial, postgres_session=session)
    async with social:
        return await social.search_users(prompt=prompt)


@social.post("/posts")
async def make_post(
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    post_data: MakePostDataSchema = Body(...)
    ) -> PostSchema:
    social, user = await create_main_service_refresh_user(MainService=MainServiceSocial, postgres_session=session, user=user_)
    async with social:
        return await social.construct_and_flush_post(data=post_data, user=user)


@social.patch("/posts/{post_id}")
async def change_post(
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    post_data: PostDataSchemaID = Body(...)
) -> PostSchema:
    social, user = await create_main_service_refresh_user(MainService=MainServiceSocial, postgres_session=session, user=user_)
    async with social:
        await social.change_post(post_data=post_data, user=user)

@social.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
) -> None:
    social, user = await create_main_service_refresh_user(MainService=MainServiceSocial, postgres_session=session, user=user)
    async with social:
        await social.delete_post(post_id=post_id, user=user)

@social.post("/posts/{post_id}/like")
async def like_post(
    post_id: str | None,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
):
    social, user = await create_main_service_refresh_user(MainService=MainServiceSocial, postgres_session=session, user=user)
    async with social:
        await social.like_post(post_id=post_id, user=user)

@social.delete("/posts/{post_id}/like")
async def unlike_post(
    post_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> None:
    social, user = await create_main_service_refresh_user(MainService=MainServiceSocial, postgres_session=session, user=user)
    async with social:
        await social.unlike_post(post_id=post_id, user=user)

@social.post("/users/{follow_to_id}/follow")
async def follow(
    follow_to_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
) -> None:
    social, user = await create_main_service_refresh_user(MainService=MainServiceSocial, postgres_session=session, user=user)
    async with social:
        await social.friendship_action(user=user, other_user_id=follow_to_id, follow=True)

@social.delete("/users/{follow_to_id}/follow")
async def unfollow(
    follow_to_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
) -> None:
    social, user = await create_main_service_refresh_user(MainService=MainServiceSocial, postgres_session=session, user=user)
    async with social:
        await social.friendship_action(user=user, other_user_id=follow_to_id, follow=False)

@social.patch("/users/my-profile/password")
async def change_password() -> UserProfileSchema:
    pass

@social.patch("/users/my-profile/username")
async def change_username() -> UserProfileSchema:
    pass

@social.get("/users/{user_id}")
async def get_user_profile(
    user_id: str | None,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    )-> UserProfileSchema:
    social, user = await create_main_service_refresh_user(MainService=MainServiceSocial, postgres_session=session, user=user)
    async with social:
        pass

@social.get("users/my-profile")
async def get_my_profile(
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    ):
    social, user = await create_main_service_refresh_user(MainService=MainServiceSocial, postgres_session=session, user=user)
    async with social:
        pass

@social.delete("/users/my-profile")
async def delete_user_account() -> None:
    pass