from databases_manager.postgres_manager.database_utils import get_session
from databases_manager.postgres_manager.models import User

from fastapi import Header, HTTPException

from dotenv import load_dotenv
from os import getenv

PASSWORD_MIN_L = int(getenv("PASSWORD_MIN_L"))
PASSWORD_MAX_L = int(getenv("PASSWORD_MAX_L"))

async def authrorize_request_depends(token: str = Header(..., title="Authorization token", example="Bearer (token)")):
    from databases_manager.main_databases_manager import MainServiceAuth
    """User with fastAPI Depends()"""
    session = get_session()
    service = await MainServiceAuth.initialize(postgres_session=session)
    user: User = await service.authorize_request(token=token, return_user=True)
    await service.finish(commit_postgres=False)
    return user

def validate_password(password: str) -> None:
    """Raises HTTPexception if password not secure enough"""

    valid_flag = True

    valid_flag = any(char.isdigit() for char in password)
    valid_flag = any(char.isupper() for char in password)

    if not PASSWORD_MIN_L <= len(password) <= PASSWORD_MAX_L or not valid_flag:
        raise HTTPException(status_code=400, detail="Password is not secure enough.")