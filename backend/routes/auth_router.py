from fastapi import APIRouter, Depends, Body, Header, HTTPException
from databases_manager.postgres_manager.database_utils import get_session_depends
from databases_manager.main_managers.main_manager_creator_abs import MainServiceContextManager
from databases_manager.main_managers.auth_manager import MainServiceAuth
from databases_manager.postgres_manager.models import User
from authorization.authorization import authorize_request_depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic_schemas.pydantic_schemas_auth import (
    LoginSchema,
    RegisterSchema,
    RefreshAccesTokens,
    RefreshTokenSchema,
    AccesTokenSchema,
    UserProfileSchema,
    RefreshAccesTokensProvided
)
from authorization import password_manager, jwt_manager

auth = APIRouter()

@auth.post("/login")
async def login(
    credentials: LoginSchema = Body(...),
    session: AsyncSession = Depends(get_session_depends)
    ) -> RefreshAccesTokens:
    async with await MainServiceContextManager[MainServiceAuth].create(MainServiceType=MainServiceAuth, postgres_session=session) as main_service:
        response = await main_service.login(credentials=credentials)
        return response

@auth.post("/register")
async def register(
    credentials: RegisterSchema = Body(...),
    session: AsyncSession = Depends(get_session_depends)
    ) -> RefreshAccesTokens:
    async with await MainServiceContextManager[MainServiceAuth].create(MainServiceType=MainServiceAuth, postgres_session=session) as main_service:
        response = await main_service.register(credentials=credentials)
        return response


@auth.post("/logout")
async def logout(
    session: AsyncSession = Depends(get_session_depends),
    tokens:RefreshAccesTokensProvided = Body(...)
) -> None:
    async with await MainServiceContextManager[MainServiceAuth].create(MainServiceType=MainServiceAuth, postgres_session=session) as main_service:
        response = await main_service.logout(tokens=tokens)
        return response

@auth.get("/refresh")
async def refresh_token(
    token = Header(..., examples="Bearer (refresh_token)"),
    session: AsyncSession = Depends(get_session_depends)
) -> AccesTokenSchema:
    async with await MainServiceContextManager[MainServiceAuth].create(MainServiceType=MainServiceAuth, postgres_session=session) as main_service:
        response = await main_service.refresh_token(refresh_token=token)
        print(response)
        return response
