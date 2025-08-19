from databases_manager.postgres_manager.database_utils import get_session
from databases_manager.postgres_manager.models import User

from fastapi import Header, HTTPException

from dotenv import load_dotenv
from os import getenv
from typing import Callable

PASSWORD_MIN_L = int(getenv("PASSWORD_MIN_L"))
PASSWORD_MAX_L = int(getenv("PASSWORD_MAX_L"))


async def authorize_request_depends(token: str = Header(..., title="Authorization acces token", examples="Bearer (token)")) -> User | None:
    """User with fastAPI Depends()"""

    # To prevent circular import
    from databases_manager.main_managers.services_creator_abstractions import MainServiceContextManager
    from databases_manager.main_managers.auth_manager import MainServiceAuth

    session = await get_session()
    async with await MainServiceContextManager[MainServiceAuth].create(MainServiceType=MainServiceAuth, postgres_session=session) as auth:
        return await auth.authorize_request(token=token, return_user=True)


def validate_password(password: str) -> None:
    """Raises HTTPexception if password not secure enough"""

    valid_flag = True

    valid_flag = any(char.isdigit() for char in password)
    valid_flag = any(char.isupper() for char in password)

    if not PASSWORD_MIN_L <= len(password) <= PASSWORD_MAX_L or not valid_flag:
        raise HTTPException(status_code=400, detail="Password is not secure enough.")