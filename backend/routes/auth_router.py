from fastapi import APIRouter, Depends, Body, Header, File, UploadFile, Form
from databases_manager.postgres_manager.database_utils import get_session_depends
from databases_manager.main_managers.services_creator_abstractions import MainServiceContextManager
from databases_manager.main_managers.auth_manager import MainServiceAuth
from sqlalchemy.ext.asyncio import AsyncSession
from authorization.authorization import authorize_request_depends
from databases_manager.postgres_manager.database_utils import merge_model
from databases_manager.postgres_manager.models import User
from pydantic_schemas.pydantic_schemas_auth import (
    LoginSchema,
    RegisterSchema,
    RefreshAccesTokens,
    AccesTokenSchema,
    RefreshAccesTokensProvided,
    OldNewPassword,
    NewUsername
)
from pydantic_schemas.pydantic_schemas_social import UserSchema

auth = APIRouter()

@auth.post("/login")
async def login(
    credentials: LoginSchema = Body(...),
    session: AsyncSession = Depends(get_session_depends)
    ) -> RefreshAccesTokens:
    async with await MainServiceContextManager[MainServiceAuth].create(MainServiceType=MainServiceAuth, postgres_session=session) as auth:
        response = await auth.login(credentials=credentials)
        return response

@auth.post("/register")
async def register(
    credentials: RegisterSchema = Body(...),
    session: AsyncSession = Depends(get_session_depends)
    ) -> RefreshAccesTokens:
    async with await MainServiceContextManager[MainServiceAuth].create(MainServiceType=MainServiceAuth, postgres_session=session) as auth:
        response = await auth.register(credentials=credentials)
        return response

@auth.post("/logout")
async def logout(
    session: AsyncSession = Depends(get_session_depends),
    tokens:RefreshAccesTokensProvided = Body(...)
) -> None:
    async with await MainServiceContextManager[MainServiceAuth].create(MainServiceType=MainServiceAuth, postgres_session=session) as auth:
        response = await auth.logout(tokens=tokens)
        return response

@auth.get("/refresh")
async def refresh_token(
    token = Header(..., examples="Bearer (refresh_token)"),
    session: AsyncSession = Depends(get_session_depends)
) -> AccesTokenSchema:
    async with await MainServiceContextManager[MainServiceAuth].create(MainServiceType=MainServiceAuth, postgres_session=session) as auth:
        response = await auth.refresh_token(refresh_token=token)
        return response

@auth.patch("/users/my-profile/password")
async def change_password(
    credentials: OldNewPassword = Body(...),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> UserSchema:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceAuth].create(postgres_session=session, MainServiceType=MainServiceAuth) as auth:
        await auth.change_password(user=user, credentials=credentials)

@auth.patch("/users/my-profile/username")
async def change_username(
    credentials: NewUsername = Body(...),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> UserSchema:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceAuth].create(postgres_session=session, MainServiceType=MainServiceAuth) as auth:
        await auth.change_username(user=user, credentials=credentials)
 
@auth.delete("/users/my-profile")
async def delete_profile(
    password: str = Header(...),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> None:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainServiceAuth].create(postgres_session=session, MainServiceType=MainServiceAuth) as auth:
        await auth.delete_user(password=password, user=user)