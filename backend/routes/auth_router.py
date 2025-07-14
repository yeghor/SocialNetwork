from fastapi import APIRouter, Depends, Body, Header
from databases_manager.postgres_manager.database_utils import get_session_depends
from databases_manager.main_databases_manager import MainService
from databases_manager.postgres_manager.models import User
from authorization.authorization import authrorize_request_depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic_schemas import (
    TokenResponseSchema,
    LoginSchema,
    RegisterSchema,
    LogoutRequest
)
from authorization import password_manager, jwt_manager

auth = APIRouter()

@auth.post("/login")
async def login(
    credentials: LoginSchema = Body(...),
    session: AsyncSession = Depends(get_session_depends)
    ) -> TokenResponseSchema:
    main_service = await MainService.initialize(postgres_session=session)
    response = await main_service.login(credentials=credentials)
    await main_service.finish(commit_postgres=True)
    return response

@auth.post("/register")
async def register(
    credentials: RegisterSchema = Body(...),
    session: AsyncSession = Depends(get_session_depends)
    ) -> TokenResponseSchema:
    main_service = await MainService.initialize(postgres_session=session)
    response = await main_service.register(credentials=credentials) 
    await main_service.finish(commit_postgres=True)
    return response

@auth.post("/logout")
async def logout(
    session: AsyncSession = Depends(get_session_depends),
    credentials: LogoutRequest = Body(...)
) -> None:
    main_service = await MainService.initialize(postgres_session=session)
    await main_service.logout(credentials=credentials)
    await main_service.finish(commit_postgres=False)

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
