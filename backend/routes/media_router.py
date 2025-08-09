from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import Response

from authorization.authorization import authorize_request_depends
from databases_manager.postgres_manager.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from databases_manager.main_managers.services_creator_abstractions import MainServiceContextManager
from databases_manager.main_managers.media_manager import MainMediaService
from databases_manager.postgres_manager.database_utils import get_session_depends, merge_model
media_router = APIRouter()

# https://stackoverflow.com/questions/55873174/how-do-i-return-an-image-in-fastapi
@media_router.get("/media/users/{token}", response_class=Response)
async def get_image(
    token: str,
    session: AsyncSession = Depends(get_session_depends)
):
    async with await MainServiceContextManager[MainMediaService].create(MainServiceType=MainMediaService, postgres_session=session) as media:  
        file_contents = await media.get_user_avatar_by_token(token=token)
        return Response(content=file_contents, media_type=)

@media_router.get("/media/posts/{token}/{number}", response_class=Response)
async def get_image(
    token: str,
    number: int,
    session: AsyncSession = Depends(get_session_depends)
):
    async with await MainServiceContextManager[MainMediaService].create(MainServiceType=MainMediaService, postgres_session=session) as media:  
        file_contents = await media.get_user_avatar_by_token(token=token)
        return Response(content=file_contents, media_type=)

# TODO: Implement file passing.
@media_router.post("/media/posts/{post_id}/{number}")
async def upload_post_picture(
    post_id: str,
    number: str,
    file: UploadFile = File(...),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> None:
    user = await merge_model(postgres_session=session, user_=user_)
    async with await MainServiceContextManager[MainMediaService].create(MainServiceType=MainMediaService, postgres_session=session) as media:
        file_contents = await file.read()
        await media.upload_post_image(post_id=post_id, user=user, number=number, image_contents=file_contents, specified_mime=file.content_type)

@media_router.post("/media/users/{user_id}")
async def upload_user_avatar(
    user_id: str,
    file: UploadFile = File(...),
    user_: User = Depends(authorize_request_depends),
    session: AsyncSession = Depends(get_session_depends)
) -> None:
    user = await merge_model(postgres_session=session, user_=user_)
    async with await MainServiceContextManager[MainMediaService].create(MainServiceType=MainMediaService, postgres_session=session) as media:
        file_contents = await file.read()
        await media.upload_user_avatar(user=user, image_contents=file_contents, specified_mime=file.content_type)