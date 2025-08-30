from fastapi import HTTPException

from services.core_services import MainServiceBase
from services.postgres_service import User, Post, PostImage
from services_types import ImageType
from exceptions.custom_exceptions import EmptyPostsError
from typing import Tuple, Literal
import mimetypes
import os
import aiofiles
from uuid import uuid4

from exceptions.exceptions_handler import web_exceptions_raiser

MEDIA_AVATAR_PATH = os.getenv("MEDIA_AVATAR_PATH", "media/users/")
MEDIA_POST_IMAGE_PATH = os.getenv("MEDIA_POST_IMAGE_PATH", "media/posts/")
MAX_NUMBER_POST_IMAGES = int(os.getenv("MAX_NUMBER_POST_IMAGES", "3"))

MEDIA_AVATAR_PATH = os.getenv("MEDIA_AVATAR_PATH", "media/users/")
MEDIA_POST_IMAGE_PATH = os.getenv("MEDIA_POST_IMAGE_PATH", "media/posts/")
MEDIA_AVATAR_PATH_TEST = os.getenv("MEDIA_AVATAR_PATH_TEST", "media/testing_media/users")
MEDIA_POST_IMAGE_PATH_TEST = os.getenv("MEDIA_POST_IMAGE_PATH_TEST", "media/testing_media/posts")


class MainMediaService(MainServiceBase):
    @staticmethod
    def _define_image_name(id_: str, image_type: ImageType, n_image: int = None) -> str:
        """Pass `n_image` only if `image_type` set to `'post'`"""
        if image_type == "post":
            if not isinstance(n_image, int): raise ValueError("No valid post image number wasn't specified")
            return f"{id_}-{n_image}"
        if image_type == "user": return id_
        else: raise ValueError("Unsupported image type!")

    @staticmethod
    async def _read_contents_and_mimetype_by_filepath(filepath: str) -> Tuple[bytes, str]:
        """Returns (`bytes`, `str`) where `bytes` - image contents, `str` - mimetype"""
        async with aiofiles.open(file=filepath, mode="rb") as file_:
            contents = await file_.read()
        
        # Return value is a tuple (type, encoding) where type is None if the type can't be guessed
        content_type = mimetypes.guess_type(filepath)[0]

        if not content_type:
            raise HTTPException(status_code=500, detail="Image content type can't be guessed. Please, try againg later")

        return (contents, content_type)

    @web_exceptions_raiser
    async def get_name_and_check_token(self, token: str, image_type: ImageType):
        """
        Get image name from Redis. If it's not exist - raises HTTPexception 401 \n
        """
        image_name = await self._RedisService.check_image_access(url_image_token=token, image_type=image_type)

        if image_name: return image_name
        raise HTTPException(status_code=401, detail="Expired or invalid token")
    
    @web_exceptions_raiser
    async def upload_post_image(self, post_id: str, user: User, image_contents: bytes, specified_mime: str) -> None:
        if image_contents and specified_mime:
            post = await self._PostgresService.get_entry_by_id(id_=post_id, ModelType=Post)

            if not post: 
                raise HTTPException(status_code=404, detail="Post with this id not found")

            if post.owner_id != user.user_id:
                raise HTTPException(status_code=401, detail="You are not the owner of this post")

            if len(post.images) >= MAX_NUMBER_POST_IMAGES:
                raise HTTPException(status_code=400, detail="Max number of post images reached")

            image_name = self._define_image_name(id_=post_id, image_type="post", n_image=len(post.images))
            image_entry = PostImage(image_id=str(uuid4()), post_id=post_id, image_name=image_name)
            await self._PostgresService.insert_models_and_flush(image_entry)

            await self._ImageStorage.upload_images_post(contents=image_contents, content_type=specified_mime, image_name=image_name)
        else: raise HTTPException(status_code=400, detail="Image type or contents missing")

    @web_exceptions_raiser
    async def upload_user_avatar(self, user: User, image_contents: bytes, specified_mime: str):
        if image_contents and specified_mime:
            if user.avatar_image_name:
                    await self._ImageStorage.delete_avatar_user(user_id=user.user_id)
 
            await self._ImageStorage.upload_avatar_user(contents=image_contents, content_type=specified_mime, image_name=user.user_id)

            user.avatar_image_name = user.user_id
            await self._PostgresService.flush()

        else: raise HTTPException(status_code=400, detail="Image type or contents missing")        

    @web_exceptions_raiser
    async def get_user_avatar_by_token(self, token: str) -> Tuple[bytes, str]:
        """Returns single image (contents, mime_type) from granted token"""
        avatar_name = await self.get_name_and_check_token(token=token, image_type="user")

        filepath = f"{MEDIA_AVATAR_PATH}{avatar_name}"
        return await self._read_contents_and_mimetype_by_filepath(filepath=filepath)

    @web_exceptions_raiser
    async def get_post_image_by_token(self, token: str) -> Tuple[bytes, str]:
        """Returns single image (contents, mime_type) from granted token"""

        image_name = await self.get_name_and_check_token(token=token, image_type="post")

        filepath = f"{MEDIA_POST_IMAGE_PATH}{image_name}"

        return await self._read_contents_and_mimetype_by_filepath(filepath=filepath)
    