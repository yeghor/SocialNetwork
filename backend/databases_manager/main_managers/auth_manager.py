from databases_manager.main_managers.main_manager_creator_abs import MainServiceBase, MainServiceContextManagerABS

from authorization import password_manager, jwt_manager
from databases_manager.postgres_manager.models import User, Post
from pydantic_schemas.pydantic_schemas_auth import (
    RegisterSchema,
    RefreshTokenSchema,
    AccesTokenSchema,
    LoginSchema,
    RefreshAccesTokens
    )

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from typing import List        

class MainServiceAuth(MainServiceBase):
    async def authorize_request(self, token: str, return_user: bool = True) -> User | None:
        """Can be used in fastAPI Depends() \n Prepares and authorizes token"""
        
        valid_token = self._JWT.prepare_token(jwt_token=token)

        if not await self._RedisService.check_jwt_existence(jwt_token=valid_token, token_type="acces"):
            raise HTTPException(status_code=401, detail="Invalid or expires token")
        
        if return_user:
            payload = self._JWT.extract_jwt_payload(jwt_token=valid_token)
            return await self._PostgresService.get_user_by_id(payload.user_id)
        
        return None

    async def register(self, credentials: RegisterSchema) -> RefreshAccesTokens:
        if await self._PostgresService.get_user_by_username_or_email(username=credentials.username, email=credentials.email):
            raise HTTPException(status_code=409, detail="Registered account with these credetials already exists")

        password_hash = password_manager.hash_password(credentials.password)
        new_user = User(
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

    async def refresh_token(self, refresh_token: RefreshTokenSchema) -> AccesTokenSchema:
        if not await self._RedisService.check_jwt_existence(jwt_token=refresh_token.refresh_token):
            raise HTTPException(status_code=401, detail="Expired or invalid refresh token")
        

        payload = self._JWT.extract_jwt_payload(jwt_token=refresh_token.refresh_token)
        user_id = payload.user_id

        old_acces_token = await self._RedisService.get_token_by_user_id(user_id=user_id, token_type="acces")
        new_acces_token = await self._JWT.generate_token(user_id=user_id, redis=self._RedisService, token_type="acces")

        await self._RedisService.refresh_acces_token(old_token=old_acces_token, new_token=new_acces_token, user_id=user_id)