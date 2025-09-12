from authorization import jwt_service
from services.core_services import MainServiceBase
from services.postgres_service import Post, User
from authorization import password_utils
from pydantic_schemas.pydantic_schemas_auth import (
    RegisterSchema,
    RefreshTokenSchema,
    AccesTokenSchema,
    LoginSchema,
    RefreshAccesTokens,
    OldNewPassword,
    NewUsername
)

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile
from fastapi import HTTPException
from uuid import uuid4
import os

from exceptions.exceptions_handler import web_exceptions_raiser
from exceptions.custom_exceptions import *

POST_IMAGE_MAX_SIZE_MB = int(os.getenv("POST_IMAGE_MAX_SIZE_MB", "25"))

class MainServiceAuth(MainServiceBase):
    @web_exceptions_raiser
    async def authorize_request(self, token: str, return_user: bool = True) -> User | None:
        """Can be used in fastAPI Depends() \n Prepares and authorizes token"""
        
        valid_token = self._JWT.prepare_token(jwt_token=token)

        if not await self._RedisService.check_jwt_existence(jwt_token=valid_token, token_type="acces"):
            raise Unauthorized(detail=f"AuthService: User tried to authrorize request by expired token: {token}", client_safe_detail="Invalid or expired token")
        
        if return_user:
            payload = self._JWT.extract_jwt_payload(jwt_token=valid_token)
            user = await self._PostgresService.get_user_by_id(payload.user_id)
            if not user:
                raise Unauthorized(detail=f"AuthService: User tried to authorize request by token: {token}, but specified user id does not exist.", client_safe_detail="Invalid or expired token")
            return user
        
        return None

    @web_exceptions_raiser
    async def authorize_chat_token(self, token: str) -> str:
        """Returns original token"""

        if not await self._RedisService.check_chat_token_existense(chat_token=token):
            raise UnauthorizedExc(dev_log_detail=f"AuthService: User tried to connected to th ws chat by expired chat token: {token}", client_safe_detail="Invalid or expired token")
        
        return token

    # TODO: Invalid password is passing.
    @web_exceptions_raiser
    async def register(self, credentials: RegisterSchema) -> RefreshAccesTokens:
        if await self._PostgresService.get_user_by_username_or_email(username=credentials.username, email=credentials.email):
            raise Collision(detail=f"AuthService: User tried to register with credentials: {credentials.username}, {credentials.email} that already exist.", client_safe_detail="Registered user with these credentials already exist")

        new_user = User(
            user_id=str(uuid4()),
            username=credentials.username, 
            email=credentials.email,
            password_hash=password_utils.hash_password(credentials.password)
        )

        await self._PostgresService.insert_models_and_flush(new_user)

        return await self._JWT.generate_save_refresh_acces_token(user_id=new_user.user_id, redis=self._RedisService)

    @web_exceptions_raiser
    async def login(self, credentials: LoginSchema) -> RefreshAccesTokens:
        potential_user = await self._PostgresService.get_user_by_username_or_email(username=credentials.username, email=None)
        if not potential_user:
            raise InvalidResourceProvided(detail=f"AuthService: User tried to login to not existing account with credentials: {credentials.username}", client_safe_detail="Account with these credentials does not exist. You may need to sign up first")
        
        if not password_utils.check_password(credentials.password, potential_user.password_hash):
            raise Unauthorized(detail=f"AuthService: User with credentials: {credentials.username} tried to login with wrong password.", client_safe_detail="Password didn't match")
        
        user_id = potential_user.user_id
        potential_refresh_token = await self._RedisService.get_token_by_user_id(user_id=user_id, token_type="refresh")
        potential_acces_token = await self._RedisService.get_token_by_user_id(user_id=user_id, token_type="acces")

        if potential_acces_token:
            await self._RedisService.delete_jwt(jwt_token=potential_acces_token, token_type="acces")
        if potential_refresh_token:
            await self._RedisService.delete_jwt(jwt_token=potential_refresh_token, token_type="refresh")
        
        return await self._JWT.generate_save_refresh_acces_token(user_id=user_id, redis=self._RedisService)

    @web_exceptions_raiser
    async def logout(self, tokens: RefreshAccesTokens) -> None:
        await self._RedisService.delete_jwt(jwt_token=tokens.acces_token, token_type="acces")
        await self._RedisService.delete_jwt(jwt_token=tokens.refresh_token, token_type="refresh")

    @web_exceptions_raiser
    async def refresh_token(self, refresh_token: str) -> AccesTokenSchema:
        prepared_token = self._JWT.prepare_token(jwt_token=refresh_token)
        if not await self._RedisService.check_jwt_existence(jwt_token=prepared_token, token_type="refresh"):
            raise Unauthorized(detail=F"AuthService: User with refresh token: {refresh_token} that does not exist tried to refresh tokens.", client_safe_detail="Invalid or expired token")
        

        payload = self._JWT.extract_jwt_payload(jwt_token=prepared_token)
        user_id = payload.user_id

        old_acces_token = await self._RedisService.get_token_by_user_id(user_id=user_id, token_type="acces")
        new_acces_token = await self._JWT.generate_save_token(user_id=user_id, redis=self._RedisService, token_type="acces")

        await self._RedisService.refresh_acces_token(old_token=old_acces_token, new_token=new_acces_token.acces_token, user_id=user_id)
        return new_acces_token
    
    @web_exceptions_raiser
    async def change_password(self, user: User, credentials: OldNewPassword) -> None:
        if not password_utils.check_password(entered_pass=credentials.old_password, hashed_pass=user.password_hash):
            raise InvalidResourceProvided(detail=f"AuthService: User: {user.user_id} tried to change password, but old password didn't match.", client_safe_detail="Password didn't match")

        new_password_hashed = password_utils.hash_password(raw_pass=credentials.new_password)
        await self._PostgresService.change_field_and_flush(model=user, password_hash=new_password_hashed)

    @web_exceptions_raiser
    async def change_username(self, user: User, credentials: NewUsername) -> None:
        new_username = credentials.new_username

        if user.username == credentials.new_username:
            raise InvalidResourceProvided(detail=f"AuthService: User: {user.user_id} tried to change username to identical to his old one.", client_safe_detail="New username can't the same as old one")

        await self._PostgresService.change_field_and_flush(model=User, username=new_username)

    @web_exceptions_raiser
    async def delete_user(self, password: str, user: User) -> None:
        if not password_utils.check_password(entered_pass=password, hashed_pass=user.password_hash):
            raise InvalidResourceProvided(detail=f"AuthService: User: {user.user_id} tried to delete his profile, but password didn't match.", client_safe_detail="Password didn't match")
        
        await self._PostgresService.delete_models_and_flush(user)
        await self._RedisService.deactivate_tokens_by_id(user_id=user.user_id)
        await self._ImageStorage.delete_avatar_user(user_id=user.user_id)
