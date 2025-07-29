from fastapi import APIRouter, Depends, Body, Query, HTTPException
from databases_manager.postgres_manager.database_utils import get_session_depends, merge_model
from databases_manager.main_managers.main_manager_creator_abs import MainServiceContextManager
from databases_manager.main_managers.social_manager import MainServiceSocial
from authorization.authorization import authorize_request_depends
from pydantic_schemas.pydantic_schemas_social import (
    UserLiteSchema,
    PostBase,
    PostLiteShortSchema,
    PostSchema,
    MakePostDataSchema,
    PostDataSchemaBase,
    UserSchema
)
from databases_manager.postgres_manager.models import User
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


@social.get("/posts/history-related")
async def get_related_to_history_posts(
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    ) -> List[PostLiteShortSchema]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.get_related_posts(user=user)

@social.get("/posts/following")
async def get_followed_posts(
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
    ) -> List[PostLiteShortSchema]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.get_followed_posts(user=user)

@social.get("/search/posts")
async def search_posts(
    prompt: str = Depends(query_prompt_required),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
    ) -> List[PostLiteShortSchema]:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.search_posts(prompt=prompt, user=user)

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
        print("Validated user data")
        return await social.construct_and_flush_post(data=post_data, user=user)

@social.get("/posts/{post_id}")
async def load_post(
    post_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> PostSchema:
    user = await merge_model(postgres_session=session, model_obj=user_)
    print(inspect(user))
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.load_post(user=user, post_id=post_id)

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
    follow_to_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
) -> None:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        await social.friendship_action(user=user, other_user_id=follow_to_id, follow=False)

@social.patch("/users/my-profile/password")
async def change_password() -> UserSchema:
    pass

@social.patch("/users/my-profile/username")
async def change_username() -> UserSchema:
    pass

@social.get("/users/{user_id}")
async def get_user_profile(
    user_id: str | None,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    )-> UserSchema:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.get_user_profile(request_user=user, other_user_id=user_id)

@social.get("/users/my-profile")
async def get_my_profile(
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends),
    ) -> UserSchema:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(postgres_session=session, MainServiceType=MainServiceSocial) as social:
        return await social.get_user_profile(request_user=user, other_user_id=user.user_id)

@social.delete("/users/my-profile")
async def delete_user_account() -> None:
    pass