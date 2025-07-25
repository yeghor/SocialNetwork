from fastapi import APIRouter, Depends, Body, Query
from pydantic_schemas.pydantic_schemas_auth import UserProfileSchema
from databases_manager.postgres_manager.database_utils import get_session_depends, refresh_model
from databases_manager.main_managers.main_manager_creator_abs import MainServiceContextManager
from databases_manager.main_managers.social_manager import MainServiceSocial
from authorization.authorization import authrorize_request_depends

social = APIRouter()

@social.get("/get_related_to_history_posts")
async def get_related_to_history_posts(
    user_ = Depends(authrorize_request_depends),
    session = Depends(get_session_depends)
):
    user = await refresh_model(session=session, model_object=user_)
    async with await MainServiceContextManager[MainServiceSocial].create(MainServiceType=MainServiceSocial, postgres_session=session) as social:
        return await social.get_related_posts(user=user)

@social.get("/get_subscribers_posts")
async def get_subscribers_posts():
    pass

@social.get("/search_posts")
async def search_posts():
    pass

@social.get("/search_users")
async def search_users():
    pass

@social.post("/make_post")
async def make_post():
    pass

@social.patch("/change_post")
async def change_post():
    pass

@social.delete("/delete_post")
async def delete_post():
    pass

@social.post("/like_post")
async def like_post():
    pass

@social.post("/leave_comment")
async def leave_comment():
    pass

@social.post("/like_comment")
async def like_comment():
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