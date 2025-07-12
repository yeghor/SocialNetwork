from fastapi import APIRouter, Depends, Body
from databases_manager.postgres_manager.database_utils import get_session_depends
from databases_manager.main_databases_manager import MainService
from databases_manager.postgres_manager.models import User
from authorization.authorization import authrorize_request_depends
from sqlalchemy.ext.asyncio import AsyncSession
from schemas import (
    TokenResponseSchema,
    LoginSchema,
    RegisterSchema
)
from authorization import password_manager, jwt_manager

auth = APIRouter()

@auth.post("/login")
async def login(credentials: LoginSchema = Body(...)):
    pass

@auth.post("/register")
async def register(
    credentials: RegisterSchema = Body(...),
    session: AsyncSession = Depends(get_session_depends)
    ):
    main_service = await MainService.initialize(postgres_session=session)
    return await main_service.register(credentials=credentials)
    

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
