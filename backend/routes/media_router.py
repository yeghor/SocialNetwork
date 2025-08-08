from fastapi import APIRouter
from fastapi.responses import Response

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

@media_router.post("/media/posts/{post_id}/{number}")
async def upload_post_picture(
    post_id: str,
    number: str
) -> None:
    pass

@media_router.post("/media/users/{user_id}")
async def upload_post_picture(
    user_id: str,
) -> None:
    pass