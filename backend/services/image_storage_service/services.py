import magic
import mimetypes
from abc import ABC, abstractmethod

from services.redis_service import RedisService

from aiobotocore.session import get_session
from botocore.exceptions import HTTPClientError
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from typing import List, Literal, Dict
import glob

from exceptions.custom_exceptions import *

# LocalStorage service can't be async. So I use aiofiles's run_in_executor() wrap
import aiofiles

load_dotenv()
POST_IMAGE_MAX_SIZE_MB = int(os.getenv("POST_IMAGE_MAX_SIZE_MB", "25"))
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_BUCKET_NAME_TEST = os.getenv("S3_BUCKET_NAME_TEST")
IMAGE_VIEW_ACCES_SECONDS = int(os.getenv("IMAGE_VIEW_ACCES_SECONDS", "180"))
MAX_NUMBER_POST_IMAGES = int(os.getenv("MAX_NUMBER_POST_IMAGES", "3"))

MEDIA_AVATAR_PATH = os.getenv("MEDIA_AVATAR_PATH", "media/users/")
MEDIA_POST_IMAGE_PATH = os.getenv("MEDIA_POST_IMAGE_PATH", "media/posts/")
MEDIA_AVATAR_PATH_TEST = os.getenv("MEDIA_AVATAR_PATH_TEST", "media/testing_media/users")
MEDIA_POST_IMAGE_PATH_TEST = os.getenv("MEDIA_POST_IMAGE_PATH_TEST", "media/testing_media/posts")


BASE_URL = os.getenv("LOCAL_BASE_URL", "http://127.0.0.1:8000")
MEDIA_POST_IMAGE_URI = os.getenv("MEDIA_POST_IMAGE_URI", "/media/posts/")
USER_AVATAR_URI = os.getenv("USER_AVATAR_URI", "media/users/")


ALLOWED_IMAGES_EXTENSIONS_MIME_RAW = os.getenv("ALLOWED_IMAGES_EXTENSIONS_MIME")
ALLOWED_EXTENSIONS = ALLOWED_IMAGES_EXTENSIONS_MIME_RAW.split(",")
for i, ext in enumerate(ALLOWED_EXTENSIONS):
    ALLOWED_EXTENSIONS[i] = ext.strip()


class DuplicateImagesExists(Exception):
    pass

# ================================

#TODO: Remove _validate_image_mime duplicates
#TODO: webp format not working
#TODO: Redis must save full image name with extension

class ImageStorageABC(ABC):
    @staticmethod
    def _validate_file_size(bytes_obj: bytes) -> bool:
        return 0 < len(bytes_obj) / 1024 / 1024 < POST_IMAGE_MAX_SIZE_MB

    @staticmethod
    def _guess_mime(file_bytes: bytes) -> str:
        return magic.from_buffer(buffer=file_bytes, mime=True)

    @abstractmethod
    def upload_images_post(self, contents: bytes, content_type: str, image_name: str):
        """
        Use for uploading and image updating. \n S3 Has only PUT options. \n
        N_image indicates number of image uploaded.
        """

    @abstractmethod
    async def upload_avatar_user(self, contents: bytes, content_type: str, image_name: str) -> None:
        """Use for uploading and image updating. \n S3 Has only PUT options."""

    @abstractmethod
    async def delete_post_images(self, image_name: str) -> None:
        """Delete n's post image. If no image - pass"""

    @abstractmethod
    async def delete_avatar_user(self, user_id: str) -> None:
        """Deletes user avatar. If not image - pass"""

    @abstractmethod
    async def get_post_image_urls(self, images_names: str) -> List[str]:
        """Get temprorary n's post image URL with jwt token in URL including. Returns empty list, if not post image"""

    @abstractmethod
    async def get_user_avatar_url(self, user_id: str) -> str | None:
        """Returns temprorary user avatar URL. Returns None, if no user avatar"""

# =======================

class S3Storage(ImageStorageABC):
    def _validate_image_mime(self, image_bytes: bytes, specified_mime: str) -> bool:    
        """Validate specified mime_type"""
        #TODO: Could reject valid file
        extension_mime = self._guess_mime(file_bytes=image_bytes)
        splitted_mime = extension_mime.split("/")

        if len(splitted_mime) != 2:
            return False

        if not extension_mime.startswith("image/"):
            return False
        
        if not splitted_mime[1] in ALLOWED_EXTENSIONS:
            return False
        
        if extension_mime != specified_mime:
            return False
        
        return True

    def __init__(self, mode: Literal["prod", "test"]):
        self._session = get_session()

        if mode == "prod": self._bucket_name = S3_BUCKET_NAME
        elif mode == "test": self._bucket_name = S3_BUCKET_NAME_TEST
        else: raise ValueError("S3 Storage: Unsupported running mode")

    @asynccontextmanager
    async def _client(self):
        async with self._session.create_client("s3") as client:
            yield client
    
    def _define_boto_Params(self, key: str) -> Dict[str, str]:
        return {
            "Bucket": self._bucket_name, "Key": key
        }

    async def upload_images_post(self, contents: bytes, content_type: str, image_name: str) -> None:
        async with self._client() as s3:
                mime_type = content_type

                if not self._validate_image_mime(image_bytes=contents, specified_mime=mime_type):
                    raise InvalidFileMimeType(f"S3 Storage: Invalid image type. Allowed only - {ALLOWED_EXTENSIONS}")
                
                if not self._validate_file_size(bytes_obj=contents):
                    raise InvalidResourceProvided(f"S3 Storage: Image is too big. Size up to {POST_IMAGE_MAX_SIZE_MB}mb")
                
                try:
                    await s3.put_object(
                        Bucket=self._bucket_name,
                        Key=image_name,
                        Body=contents,
                        ContentType=mime_type
                    )
                except Exception as e:
                    raise MediaError(f"S3 Storage: Failed to upload post image: {e}") from e

    async def upload_avatar_user(self, contents: bytes, mime_type: str, image_name: str) -> None:
        async with self._client() as s3:
            if not self._validate_image_mime(image_bytes=contents, specified_mime=mime_type):
                raise InvalidFileMimeType(detail=f"S3 Storage: User {image_name} tried to upload avatar with wrong mime type", client_safe_detail=f"Invalid image type. Allowed only - {ALLOWED_EXTENSIONS}")
            
            if not self._validate_file_size(bytes_obj=contents):
                raise InvalidResourceProvided(detail=f"S3 Storage: User {image_name} tried to uploaded avatar bigger than {POST_IMAGE_MAX_SIZE_MB}mb", client_safe_detail=f"Image is too big. Size up to {POST_IMAGE_MAX_SIZE_MB}mb")
            
            try:
                await s3.put_object(
                    Bucket=self._bucket_name,
                    Key=image_name,
                    Body=contents,
                    ContentType=mime_type
                )
            except Exception as e:
                raise MediaError(f"S3 Storage: Failed to upload user image: {e}") from e

    # TODO: DRY this below    
    async def delete_post_images(self, image_name: str) -> None:
        async with self._client() as s3:
            try:
                await s3.delete_object(
                    Bucket=self._bucket_name,
                    Key=image_name
                )
            except Exception as e:
                raise MediaError(f"S3 Storage: Failed to delete post image: {e}") from e

    async def delete_avatar_user(self, user_id: str) -> None:
        async with self._client() as s3:
            try:
                await s3.delete_object(
                    Bucket=self._bucket_name,
                    Key=user_id
                )
            except Exception as e:
                raise MediaError(f"S3 Storage: Failed to delete user avatar: {e}") from e

    async def get_post_image_urls(self, images_names: List[str]) -> List[str]:
        async with self._client() as s3:
            urls = []
            for image_name in images_names:
                try:
                    url = await s3.generate_presigned_url(
                        "get_object",
                        Params=self._define_boto_Params(key=image_name),
                        ExpiresIn=IMAGE_VIEW_ACCES_SECONDS
                    )
                    if url:
                        urls.append(url)
                except Exception as e:
                    raise MediaError(f"S3 Storage: Failed to get post images presigned URLs. Images names: {images_names}. Exception: {e}") from e
            
            return urls

    async def get_user_avatar_url(self, user_id: str) -> str:
        async with self._client() as s3:
            try:
                return await s3.generate_presigned_url(
                    "get_object",
                    Params=self._define_boto_Params(key=user_id),
                    ExpiresIn=IMAGE_VIEW_ACCES_SECONDS
                )
            except Exception as e:
                raise MediaError(f"S3 Storage: Failed to get user avatar presigned. Image name - {user_id}. Exception: {e}") from e

import secrets

class LocalStorage(ImageStorageABC):
    def _validate_image_mime(self, image_bytes: bytes, specified_mime: str) -> bool:    
        """Validate specified mime_type"""
        #TODO: Could reject valid file
        extension_mime = self._guess_mime(file_bytes=image_bytes)
        splitted_mime = extension_mime.split("/")

        if len(splitted_mime) != 2:
            return False

        if not extension_mime.startswith("image/"):
            return False
        
        if not splitted_mime[1] in ALLOWED_EXTENSIONS:
            return False
        
        if extension_mime != specified_mime:
            return False
        
        return True

    @staticmethod
    def _generate_url_token() -> str:
        return secrets.token_urlsafe()

    def __init__(self, mode: Literal["prod", "test"], Redis: RedisService):
        self._Redis = Redis

        if mode == "prod":
            self.__media_avatar_path = MEDIA_AVATAR_PATH
            self.__media_post_path = MEDIA_POST_IMAGE_PATH
        elif mode == "test":
            self.__media_avatar_path = MEDIA_AVATAR_PATH_TEST
            self.__media_post_path = MEDIA_POST_IMAGE_PATH_TEST

    async def _validate_image(self, contents: bytes, content_type: str, image_name: str) -> None: 
        if not self._validate_image_mime(image_bytes=contents, specified_mime=content_type):
            raise InvalidFileMimeType(detail=f"Local Storage: User {image_name} tried to upload avatar with wrong mime type", client_safe_detail=f"Invalid image type. Allowed only - {ALLOWED_EXTENSIONS}")

        if not self._validate_file_size(bytes_obj=contents):
            raise InvalidResourceProvided(detail=f"Local Storage: User {image_name} tried to uploaded avatar bigger than {POST_IMAGE_MAX_SIZE_MB}mb", client_safe_detail=f"Image is too big. Size up to {POST_IMAGE_MAX_SIZE_MB}mb")

    @staticmethod
    async def _get_extension(content_type: str, image_name: str) -> str:
         # Return value is a string giving a filename extension, including the leading dot ('.') / mimetypes.guess_extension()
        extension = mimetypes.guess_extension(type=content_type)
        if not extension:
            raise InvalidFileMimeType(detail=f"Local Storage: User {image_name} tried to upload post image with corrupted mime type - {content_type}", client_safe_detail=f"Invalid image type. Allowed only - {ALLOWED_EXTENSIONS}")
        return extension

    async def upload_images_post(self, contents: bytes, content_type: str, image_name: str) -> None:
        await self._validate_image(contents=contents, content_type=content_type, image_name=image_name)
        extension = await self._get_extension(content_type=content_type, image_name=image_name)

        try:
            async with aiofiles.open(file=f"{self.__media_post_path}/{image_name}{extension}", mode="wb") as file_:
                await file_.write(contents)
        except Exception as e:
                raise MediaError(f"Local Storage: Failed write post image localy. Image name - {image_name}. Exception - {e}") from e

    async def upload_avatar_user(self, contents: bytes, content_type: str, image_name: str) -> None:
        await self._validate_image(contents=contents, content_type=content_type, image_name=image_name)
        extension = await self._get_extension(content_type=content_type, image_name=image_name)
        
        try:
            async with aiofiles.open(file=f"{self.__media_avatar_path}/{image_name}{extension}", mode="wb") as file_:
                await file_.write(contents)
        except Exception as e:
            raise MediaError(f"Local Storage: Failed write user avatar localy. Image name - {image_name}. Exception - {e}") from e

    
    async def delete_post_images(self, base_name: str) -> None:
        """Pass to `base_name` image name that includes same part, like post_id without image ordinal number"""
        # Whe don't know file extension. So we need to find it using glob and image_name*

        filenames = glob.glob(f"{base_name}*", root_dir=self.__media_post_path)
        for filename in filenames:
            filepath = f"{self.__media_post_path}{filename}"

            if os.path.exists(path=filepath):
                try:
                    os.remove(path=filepath)
                except Exception as e:
                  raise MediaError(f"Local Storage: Failed delete post image localy. Filepath - {filename}. Exception - {e}") from e
            else:
                return

    
    async def delete_avatar_user(self, user_id: str) -> None:
        # Program does not know the file extension. So we need to find it using glob and image_name*
        filenames = glob.glob(f"{user_id}*", root_dir=self.__media_avatar_path)

        if not filenames:
            return
        
        if len(filenames) > 1:
            raise ValueError("Multiple images was found. Aborting.")

        filename = filenames[0]
        filepath = f"{self.__media_avatar_path}{filename}"

        if os.path.exists(path=filepath):
            try:
                os.remove(path=filepath)
            except Exception as e:
                raise MediaError(f"Local Storage: Failed delete user avatar localy. Filepath - {filename}. Exception - {e}") from e
        else:
            return

    async def get_post_image_urls(self, images_names: List[str]) -> List[str]:
        urls = []
        for provided_filename in images_names:
            urfsafe_token = self._generate_url_token()

            filenames = glob.glob(pathname=f"{provided_filename}*", root_dir=self.__media_post_path)
            if not filenames:
                continue
            filename = filenames[0]

            await self._Redis.save_url_post_token(image_token=urfsafe_token, image_name=filename)
            url = f"{BASE_URL}{MEDIA_POST_IMAGE_URI}{urfsafe_token}"
            urls.append(url)
        return urls

    async def get_user_avatar_url(self, user_id: str) -> str | None:
        urlsafe_token = self._generate_url_token()

        # Searching for potential 
        filenames = glob.glob(f"{user_id}*", root_dir=self.__media_avatar_path)
        if not filenames:
            return None
        filename = filenames[0]

        await self._Redis.save_url_user_token(image_token=urlsafe_token, image_name=filename)
        return f"{BASE_URL}{USER_AVATAR_URI}{urlsafe_token}"
