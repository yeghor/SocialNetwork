from fastapi import HTTPException

from databases_manager.main_managers.services_creator_abstractions import MainServiceBase
from databases_manager.postgres_manager.models import User, Post, PostImage
from databases_manager.redis_manager.redis_manager import ImageType
from databases_manager.redis_manager.redis_manager import ImageType
from typing import Tuple
import mimetypes
import os

MEDIA_AVATAR_PATH = os.getenv("MEDIA_AVATAR_PATH", "media/users/")
MEDIA_POST_IMAGE_PATH = os.getenv("MEDIA_POST_IMAGE_PATH", "media/posts/")
MAX_NUMBER_POST_IMAGES = int(os.getenv("MAX_NUMBER_POST_IMAGES", "3"))

class MainMediaService(MainServiceBase):
    @staticmethod
    def _define_image_name(id_: str, image_type: ImageType, n_image: int = None) -> str:
        """Pass `n_image` only if `image_type` set to `'post'`"""
        if image_type == "post":
            if not n_image: raise ValueError("No post image number wasn't specified")
            return f"post_id:{id_}___n_image:{n_image}"
        if image_type == "user": return f"user_id:{id_}"
        else: raise ValueError("Unsupported image type!")

    @staticmethod
    async def _read_contents_and_mimetype_by_filepath(filepath: str) -> Tuple[bytes, str]:
        """Returns (`bytes`, `str`) where `bytes` - image contents, `str` - mimetype"""
        async with open(file=filepath, mode="rb") as f:
            contents = await f.read()
        
        # Return value is a tuple (type, encoding) where type is None if the type can't be guessed
        content_type = mimetypes.guess_type(filepath)[0]

        if not content_type:
            raise HTTPException(status_code=500, detail="Image content type can't be guessed. Please, try againg later")

        return (contents, content_type)

    async def get_name_and_check_token(self, token: str, image_type: ImageType, number: int | None):
        """
        Get image name from Redis. If it's not exist - raises HTTPexception 401 \n
        Pass `number` only if `image_type` set to "post"
        """
        if image_type == "post":
            image_name = await self._RedisService.check_image_access(url_image_token=token, image_type=image_type, n_image=number)
        elif image_type == "user":
            image_name = await self._RedisService.check_image_access(url_image_token=token, image_type=image_type)

        if image_name: return image_name
        raise HTTPException(status_code=401, detail="Expired or invalid token")
    
    async def upload_post_image(self, post_id: str, user: User, image_contents: bytes, specified_mime: str) -> None:
        if image_contents and specified_mime:
            post = await self._PostgresService.get_entry_by_id(id_=post_id, ModelType=Post)

            if len(post.images) >= MAX_NUMBER_POST_IMAGES:
                raise HTTPException(status_code=400, detail="Max number of post images reached")

            image_name = self._define_image_name(id_=post_id, image_type="post", n_image=len(post.images))
            image_entry = PostImage(post_id=post_id, image_name=image_name)
            await self._PostgresService.insert_models_and_flush(image_entry)

            if post.owner_id != user.user_id:
                raise HTTPException(status_code=401, detail="You are not the owner of this post")

            await self._ImageStorage.upload_image_post(contents=image_contents, content_type=specified_mime, image_name=image_name)
        else: raise HTTPException(status_code=400, detail="Image type or contents missing")

    async def upload_user_avatar(self, user: User, image_content: bytes, specified_mime: str):
        if image_content and specified_mime:
            image_name = self._define_image_name(id_=user.user_id, image_type="user")
            if user.avatar_image_name:
                await self._ImageStorage.delete_avatar_user(image_name=image_name)
            
            user.avatar_image_name = image_name
            await self._PostgresService.flush()
            
            await self._ImageStorage.upload_avatar_user(contents=image_content, specified_mime=specified_mime, image_name=image_name)
        else: raise HTTPException(status_code=400, detail="Image type or contents missing")        

    async def get_user_avatar_by_token(self, token: str) -> Tuple[bytes, str]:
        """Returns single image (contents, mime_type) from granted token"""
        avatar_name = await self.get_name_and_check_token(token=token, image_type="user")

        filepath = f"{MEDIA_AVATAR_PATH}{avatar_name}"
        return await self._read_contents_and_mimetype_by_filepath(filepath=filepath)

    async def get_post_image_by_token(self, token: str, user: User, number: int) -> Tuple[bytes, str]:
        """Returns single image (contents, mime_type) from granted token"""

        post_image_name = await self._RedisService.check_image_access(url_image_token=token, image_type="post", number=number)

        filepath = f"{MEDIA_POST_IMAGE_PATH}{post_image_name}{number}"
        return await self._read_contents_and_mimetype_by_filepath(filepath=filepath)