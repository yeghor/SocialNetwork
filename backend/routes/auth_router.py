from fastapi import APIRouter, Depends
from databases_manager.postgres_manager.database_utils import get_session_depends
from databases_manager.main_databases_manager import MainService
from databases_manager.postgres_manager.models import User
from authorization.auth_depends import authrorize_request_depends
from sqlalchemy.ext.asyncio import  AsyncSession

auth = APIRouter()

@auth.post("/login")
async def login():
    pass

@auth.post("/register")
async def register():
    pass

@auth.post("/logout")
async def logoit():
    pass

@auth.get("/refresh")
async def refresh_token():
    pass

@auth.patch("/change_password")
async def change_password():
    pass

@auth.patch("/change_username")
async def change_username():
    pass

@auth.post("/get_user_profile")
async def get_user_profile():
    pass

@auth.delete("/delete_user_profile")
async def delete_user_profile():
    pass
