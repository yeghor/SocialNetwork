from fastapi import APIRouter
from pydantic_schemas.pydantic_schemas_auth import UserProfileSchema

social = APIRouter()

@social.get("/get_related_to_history_posts")
async def get_related_to_history_posts():
    pass

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