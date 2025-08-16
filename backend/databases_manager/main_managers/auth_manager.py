from databases_manager.main_managers.services_creator_abstractions import MainServiceBase, MainServiceContextManagerABS

from authorization import password_manager, jwt_manager
from databases_manager.postgres_manager.models import User, Post
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

POST_IMAGE_MAX_SIZE_MB = int(os.getenv("POST_IMAGE_MAX_SIZE_MB", "25"))

class MainServiceAuth(MainServiceBase):
    async def authorize_request(self, token: str, return_user: bool = True) -> User | None:
        """Can be used in fastAPI Depends() \n Prepares and authorizes token"""
        
        valid_token = self._JWT.prepare_token(jwt_token=token)

        if not await self._RedisService.check_jwt_existence(jwt_token=valid_token, token_type="acces"):
            raise HTTPException(status_code=401, detail="Invalid or expires token")
        
        if return_user:
            payload = self._JWT.extract_jwt_payload(jwt_token=valid_token)
            user = await self._PostgresService.get_user_by_id(payload.user_id)
            if not user:
                raise HTTPException(status_code=401, detail="Invalid user id specified in token. Try to logout and then login again")
        
        return None

    # TODO: Cover in try except! ALL OF THIS
    async def register(self, credentials: RegisterSchema) -> RefreshAccesTokens:
        if await self._PostgresService.get_user_by_username_or_email(username=credentials.username, email=credentials.email):
            raise HTTPException(status_code=409, detail="Registered account with these credetials already exists")

        password_hash = password_manager.hash_password(credentials.password)
        new_user = User(
            user_id=str(uuid4()),
            username=credentials.username, 
            email=credentials.email,
            password_hash=password_hash
        )
        await self._PostgresService.insert_models_and_flush(new_user)

        return await self._JWT.generate_refresh_acces_token(user_id=new_user.user_id, redis=self._RedisService)

            
    async def login(self, credentials: LoginSchema) -> RefreshAccesTokens:
        potential_user = await self._PostgresService.get_user_by_username_or_email(username=credentials.username, email=None)
        if not potential_user:
            raise HTTPException(status_code=400, detail="Account with this credentials doesn't exists")
        
        if not password_manager.check_password(credentials.password, potential_user.password_hash):
            raise HTTPException(status_code=401, detail="Unathorized. Invalid credentials")
        
        user_id = potential_user.user_id
        potential_refresh_token = await self._RedisService.get_token_by_user_id(user_id=user_id, token_type="refresh")
        potential_acces_token = await self._RedisService.get_token_by_user_id(user_id=user_id, token_type="acces")

        if potential_acces_token:
            await self._RedisService.delete_jwt(jwt_token=potential_acces_token, token_type="acces")
        if potential_refresh_token:
            await self._RedisService.delete_jwt(jwt_token=potential_refresh_token, token_type="refresh")
        
        return await self._JWT.generate_refresh_acces_token(user_id=user_id, redis=self._RedisService)

    async def logout(self, tokens: RefreshAccesTokens) -> None:
        await self._RedisService.delete_jwt(jwt_token=tokens.acces_token, token_type="acces")
        await self._RedisService.delete_jwt(jwt_token=tokens.refresh_token, token_type="refresh")

    async def refresh_token(self, refresh_token: str) -> AccesTokenSchema:
        prepared_token = self._JWT.prepare_token(jwt_token=refresh_token)
        if not await self._RedisService.check_jwt_existence(jwt_token=prepared_token, token_type="refresh"):
            raise HTTPException(status_code=401, detail="Expired or invalid refresh token")
        

        payload = self._JWT.extract_jwt_payload(jwt_token=prepared_token)
        user_id = payload.user_id

        old_acces_token = await self._RedisService.get_token_by_user_id(user_id=user_id, token_type="acces")
        new_acces_token = await self._JWT.generate_save_token(user_id=user_id, redis=self._RedisService, token_type="acces")

        await self._RedisService.refresh_acces_token(old_token=old_acces_token, new_token=new_acces_token.acces_token, user_id=user_id)
        return new_acces_token
    
    async def change_password(self, user: User, credentials: OldNewPassword) -> None:
        if not password_manager.check_password(entered_pass=credentials.old_password, hashed_pass=user.password_hash):
            raise HTTPException(status_code=401, detail="Old password didn't match")

        new_password_hashed = password_manager.hash_password(raw_pass=credentials.new_password)
        await self._PostgresService.change_field_and_flush(Model=user, password_hash=new_password_hashed)

    async def change_username(self, user: User, credentials: NewUsername) -> None:
        new_username = credentials.new_username

        if user.username != credentials.new_username:
            raise HTTPException(status_code=400, detail="New username can't be the same with an old one")

        await self._PostgresService.change_field_and_flush(Model=User, username=new_username)

    async def delete_user(self, password: str, user: User) -> None:
        if not password_manager.check_password(entered_pass=password, hashed_pass=user.password_hash):
            raise HTTPException(status_code=401, detail="Password didn't match")
        
        await self._PostgresService.delete_models_and_flush(user)
        await self._RedisService.deactivate_tokens_by_id(user_id=user.user_id)
        await self._ImageStorage.delete_avatar_user(user_id=user.user_id)
       