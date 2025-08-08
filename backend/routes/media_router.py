from fastapi import APIRouter, Depends
from fastapi.responses import Response

from authorization.authorization import authorize_request_depends
from databases_manager.postgres_manager.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from databases_manager.main_managers.services_creator_abstractions import MainServiceContextManager
from databases_manager.main_managers.s3_image_storage import S3Storage
from databases_manager.postgres_manager.database_utils import get_session_depends, merge_model
media_router = APIRouter()

# https://stackoverflow.com/questions/55873174/how-do-i-return-an-image-in-fastapi
@media_router.get("/media/posts/{token}", response_class=Response)
async def get_post_picture(
    token: str
):
    pass

@media_router.get("/media/users/{token}", response_class=Response)
async def get_user_avatar(
    token: str
):
    pass

# TODO: Implement file passing.
@media_router.post("/media/posts/{post_id}/{number}")
async def upload_post_picture(
    post_id: str,
    number: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> None:
    user = await merge_model(postgres_session=session, user_=user_)
    async with await MainServiceContextManager[S3Storage].create(MainServiceType=S3Storage, postgres_session=session) as media:
        await media.upload_image_post()

@media_router.post("/media/users/{user_id}")
async def upload_user_avatar(
    user_id: str,
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> None:
    user = await merge_model(postgres_session=session, user_=user_)
    async with await MainServiceContextManager[S3Storage].create(MainServiceType=S3Storage, postgres_session=session) as media:
        await media.upload_image_post