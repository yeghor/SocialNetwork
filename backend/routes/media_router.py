from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import Response

from authorization.authorization_utils import authorize_request_depends
from services.postgres_service.models import User
from services.postgres_service.database_utils import *
from sqlalchemy.ext.asyncio import AsyncSession
from services.core_services import MainServiceContextManager
from services.core_services.main_services.main_media_service import MainMediaService

media_router = APIRouter()

"""
This router is only for case when the application use Local image storage.
"""

# https://stackoverflow.com/questions/55873174/how-do-i-return-an-image-in-fastapi
@media_router.get("/media/users/{token}", response_class=Response)
async def get_image_user(
    token: str,
    session: AsyncSession = Depends(get_session_depends)
) -> str:
    async with await MainServiceContextManager[MainMediaService].create(MainServiceType=MainMediaService, postgres_session=session) as media:  
        file_contents, mime_type = await media.get_user_avatar_by_token(token=token)
        return Response(content=file_contents, media_type=mime_type)

@media_router.get("/media/posts/{token}", response_class=Response)
async def get_image_post(
    token: str,
    session: AsyncSession = Depends(get_session_depends)
) -> str:
    async with await MainServiceContextManager[MainMediaService].create(MainServiceType=MainMediaService, postgres_session=session) as media:  
        file_contents, mime_type = await media.get_post_image_by_token(token=token)
        return Response(content=file_contents, media_type=mime_type)

# TODO: Implement file passing.
@media_router.post("/media/posts/{post_id}")
async def upload_post_picture(
    post_id: str,
    file_: UploadFile = File(...),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> None:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainMediaService].create(MainServiceType=MainMediaService, postgres_session=session) as media:
        file_contents = await file_.read()
        await media.upload_post_image(post_id=post_id, user=user, image_contents=file_contents, specified_mime=file_.content_type)

# No need to request user_id - getting it from JWT  
@media_router.post("/media/users/")
async def upload_user_avatar(
    file: UploadFile = File(...),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> None:
    user = await merge_model(postgres_session=session, model_obj=user_)
    async with await MainServiceContextManager[MainMediaService].create(MainServiceType=MainMediaService, postgres_session=session) as media:
        file_contents = await file.read()
        await media.upload_user_avatar(user=user, image_contents=file_contents, specified_mime=file.content_type)