from databases_manager.main_databases_manager import MainService
from databases_manager.postgres_manager.database_utils import get_session
from databases_manager.postgres_manager.models import User

from fastapi import Header
from typing import Annotated

async def authrorize_request_depends(token: str = Header(..., title="Authorization token", example="Bearer (token)")):
    """User with fastAPI Depends()"""
    session = get_session()
    service = await MainService.initialize(postgres_session=session)
    user: User = await service.authorize_request(token=token, return_user=True)
    await service.finish(commit_postgres=False)
    return user