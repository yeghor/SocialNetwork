from fastapi import APIRouter, Depends, Body, Header, HTTPException
from databases_manager.postgres_manager.database_utils import get_session_depends
from databases_manager.main_databases_manager import MainService
from databases_manager.postgres_manager.models import User
from authorization.authorization import authrorize_request_depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic_schemas import (
    LoginSchema,
    RegisterSchema,
    RefreshAccesTokens,
    RefreshTokenSchema,
    AccesTokenSchema,
    UserProfileSchema
)
from authorization import password_manager, jwt_manager

auth = APIRouter()

@auth.post("/login")
async def login(
    credentials: LoginSchema = Body(...),
    session: AsyncSession = Depends(get_session_depends)
    ) -> RefreshAccesTokens:
    main_service = await MainService.initialize(postgres_session=session)
    response = await main_service.login(credentials=credentials)
    await main_service.finish(commit_postgres=True)
    return response

@auth.post("/register")
async def register(
    credentials: RegisterSchema = Body(...),
    session: AsyncSession = Depends(get_session_depends)
    ) -> RefreshAccesTokens:
    main_service = await MainService.initialize(postgres_session=session)
    response = await main_service.register(credentials=credentials) 
    await main_service.finish(commit_postgres=True)
    return response


@auth.post("/logout")
async def logout(
    session: AsyncSession = Depends(get_session_depends),
    tokens: RefreshAccesTokens = Body(...)
) -> None:
    main_service = await MainService.initialize(postgres_session=session)
    response = await main_service.logout(credentials=tokens)
    await main_service.finish(commit_postgres=False)
    return response

@auth.get("/refresh")
async def refresh_token(
    token: RefreshTokenSchema = Body(...),
    session: AsyncSession = Depends(get_session_depends)
) -> AccesTokenSchema:
    main_service = await MainService.initialize(postgres_session=session)
    response = await MainService.refresh_token(refresh_token=token)
    await main_service.finish()
    return response

@auth.patch("/change_password")
async def change_password() -> UserProfileSchema:
    pass

@auth.patch("/change_username")
async def change_username() -> UserProfileSchema:
    pass

@auth.post("/get_user_profile")
async def get_user_profile() -> UserProfileSchema:
    pass

@auth.delete("/delete_user_account")
async def delete_user_account() -> None:
    pass
