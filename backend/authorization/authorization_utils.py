from services.postgres_service import get_session, User

from fastapi import Header, HTTPException

from dotenv import load_dotenv
from os import getenv
from typing import Callable

from exceptions.custom_exceptions import *
from exceptions.exceptions_handler import endpoint_exception_handler

PASSWORD_MIN_L = int(getenv("PASSWORD_MIN_L"))
PASSWORD_MAX_L = int(getenv("PASSWORD_MAX_L"))

@endpoint_exception_handler
async def authorize_request_depends(token: str = Header(..., title="Authorization acces token", examples="Bearer {token}")) -> User | None:
    """User with fastAPI Depends()"""

    # To prevent circular import
    from services.core_services import MainServiceContextManager
    from services.core_services.main_services import MainServiceAuth

    session = await get_session()
    async with await MainServiceContextManager[MainServiceAuth].create(MainServiceType=MainServiceAuth, postgres_session=session) as auth:
        return await auth.authorize_request(token=token, return_user=True)

@endpoint_exception_handler
async def authorize_chat_token(token: str) -> None:
    from services.core_services import MainServiceContextManager
    from services.core_services.main_services import MainServiceAuth

    session = await get_session()
    async with await MainServiceContextManager[MainServiceAuth].create(MainServiceType=MainServiceAuth, postgres_session=session) as auth:
        return await auth.authorize_chat_token(token=token)

@endpoint_exception_handler
def validate_password(password: str) -> None:
    """Raises HTTPexception if password not secure enough"""

    valid_flag = True

    valid_flag = any(char.isdigit() for char in password)
    valid_flag = any(char.isupper() for char in password)

    if not valid_flag:
        raise ValidationError(detail=f"Password validation failed", client_safe_detail=f"Password is too weak. At least one number and upper letter")
    
    if not PASSWORD_MIN_L <= len(password) <= PASSWORD_MAX_L:
        raise ValidationError(detail=f"Password validation failed", client_safe_detail=f"Password length is out of range. Must be from {PASSWORD_MIN_L} to {PASSWORD_MAX_L} chars.")