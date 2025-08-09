from fastapi import UploadFile
import magic
from abc import ABC, abstractmethod

from databases_manager.main_managers.services_creator_abstractions import MainServiceBase
from databases_manager.redis_manager.redis_manager import RedisService

from aiobotocore.session import get_session
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from typing import List, Literal, Tuple, Dict


load_dotenv()
POST_IMAGE_MAX_SIZE_MB = int(os.getenv("POST_IMAGE_MAX_SIZE_MB", "25"))
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_BUCKET_NAME_TEST = os.getenv("S3_BUCKET_NAME_TEST")
IMAGE_VIEW_ACCES_SECONDS = int(os.getenv("IMAGE_VIEW_ACCES_SECONDS", "180"))
MAX_NUMBER_POST_IMAGES = int(os.getenv("MAX_NUMBER_POST_IMAGES", "3"))

MEDIA_AVATAR_PATH = os.getenv("MEDIA_AVATAR_PATH", "media/users/")
MEDIA_POST_IMAGE_PATH = os.getenv("MEDIA_POST_IMAGE_PATH", "media/posts/")

ALLOWED_IMAGES_EXTENSIONS_MIME_RAW = os.getenv("ALLOWED_IMAGES_EXTENSIONS_MIME")
ALLOWED_EXTENSIONS = ALLOWED_IMAGES_EXTENSIONS_MIME_RAW.split(",")
for i, ext in enumerate(ALLOWED_EXTENSIONS):
    ALLOWED_EXTENSIONS[i] = ext.strip()

# ================================

class StorageABC():
    @abstractmethod
    def upload_image_post(self, contents: bytes, content_type: str, post_id: str, n_image: int):
        """
        Use for uploading and image updating. \n S3 Has only PUT options. \n
        N_image indicates number of image uploaded.
        """

    @abstractmethod
    async def upload_avatar_user(self, contents: bytes, specified_mime: str, user_id: str) -> None:
        """Use for uploading and image updating. \n S3 Has only PUT options."""

    @abstractmethod
    async def delete_image_post(self, post_id: str) -> None:
        """Delete n's post image"""

    @abstractmethod
    async def delete_avatar_user(self, user_id: str) -> None:
        pass

    @abstractmethod
    async def get_post_image_urls(self, post_id: str) -> List[str]:
        """Get temprorary n's post image URL with jwt token in URL including"""

    @abstractmethod
    async def get_user_avatar_url(self, post_id: str) -> List[str]:
        pass

# =======================

class S3Storage(StorageABC):
    @staticmethod
    def _validate_file_size(bytes_obj: bytes) -> bool:
        return 0 < len(bytes_obj) / 1024 / 1024 < POST_IMAGE_MAX_SIZE_MB

    @staticmethod
    def _define_image_name(id_: str, type: Literal["post", "user"], n_image: int = None) -> str:
        if type == "post":
            if not n_image: raise ValueError("No post image number wasn't specified")
            return f"post_id:{id_}___n_image:{n_image}"
        if type == "user": return f"user_id:{id_}"
        else: raise ValueError("Unsupported image type!")

    @staticmethod
    def _guess_mime(file_bytes: bytes) -> str:
        return magic.from_buffer(buffer=file_bytes, mime=True)

    def _validate_image_mime(self, image_bytes: bytes, specified_mime: str) -> bool:    
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
        else: raise ValueError("Unsupported running mode")

    @asynccontextmanager
    async def _client(self):
        async with self._session.create_client("s3") as client:
            yield client
    
    def _define_boto_Params(self, key: str) -> Dict[str, str]:
        return {
            "Bucket": self._bucket_name, "Key": key
        }

    async def upload_image_post(self, contents_list: List[bytes], mime_types: List[str], post_id: str) -> None:
        async with self._client() as s3:
            if len(contents_list) != len(mime_types):
                raise ValueError("Length of content and mime types is not equal")

            for i, contents in enumerate(contents_list):
                image_name = self._define_image_name(post_id=post_id, n_image=i)
                mime_type = mime_types[i]

                if not self._validate_image_mime(image_bytes=contents, specified_mime=mime_type):
                    raise ValueError(f"Invalid image type. Allowed only - {ALLOWED_EXTENSIONS}")
                
                if not self._validate_file_size(bytes_obj=contents):
                    raise ValueError(f"Image is too big. Size up to {POST_IMAGE_MAX_SIZE_MB}mb")
                
                try:
                    await s3.put_object(
                        Bucket=self._bucket_name,
                        Key=image_name,
                        Body=contents,
                        ContentType=mime_type
                    )
                except Exception as e:
                    raise Exception(f"Failed yo upload post image: {e}")

    async def upload_avatar_user(self, contents: bytes, mime_type: str, user_id: str) -> None:
        async with self._client() as s3:
            image_name = self._define_image_name(id_=user_id, type="user")
            if not self._validate_image_mime(image_bytes=contents, specified_mime=mime_type):
                raise ValueError(f"Invalid image type. Allowed only - {ALLOWED_EXTENSIONS}")
            
            if not self._validate_file_size(bytes_obj=contents):
                raise ValueError(f"Image is too big. Size up to {POST_IMAGE_MAX_SIZE_MB}mb")
            
            try:
                await s3.put_object(
                    Bucket=self._bucket_name,
                    Key=image_name,
                    Body=contents,
                    ContentType=mime_type
                )
            except Exception as e:
                raise Exception(f"Failed yo upload user image: {e}")
            
    async def delete_image_post(self, post_id: str) -> None:
        async with self._client as s3:
            for i in range(MAX_NUMBER_POST_IMAGES):
                image_key = self._define_image_name(id_=post_id, type="post", n_image=i)
                await s3.delete_object(
                    Bucket=self._bucket_name,
                    Key=image_key
                )

    async def delete_avatar_user(self, user_id: str) -> None:
        async with self._client as s3:
            image_key = self._define_image_name(id_=user_id, type="user")
            await s3.delete_object(
                Bucket=self._bucket_name,
                Key=image_key
            )

    async def get_post_image_urls(self, post_id: str) -> List[str]:
        async with self._client as s3:
            urls = []
            for i in range(MAX_NUMBER_POST_IMAGES):
                image_key = self._define_image_name(id_=post_id, type="post", n_image=i)
                url = await s3.generate_presigned_url(
                    "get_object",
                    Params=self._define_boto_Params(key=image_key),
                    ExpiresIn=IMAGE_VIEW_ACCES_SECONDS
                )
                if url:
                    urls.append(url)
            
            return urls

    async def get_user_avatar_url(self, user_id: str) -> str:
        async with self._client as s3:
            image_key = self._define_image_name(id_=user_id, type="user")
            return await s3.generate_presigned_url(
                "get_object",
                Params=self._define_boto_Params(key=image_key),
                ExpiresIn=IMAGE_VIEW_ACCES_SECONDS
            )

import secrets
import random

class LocalStorage(StorageABC):
    @staticmethod
    def generate_url_token() -> str:
        return secrets.token_urlsafe()

    def __init__(self, Redis: RedisService):
            self._Redis = Redis

    def upload_image_post(self, contents: bytes, content_type: str, post_id: str, n_image: int):
        pass

    async def upload_avatar_user(self, contents: bytes, extension: str, user_id: str) -> None:
        pass

    async def delete_image_post(self, post_id: str) -> None:
        pass

    async def delete_avatar_user(self, user_id: str) -> None:
        pass

    async def get_post_image_urls(self, post_id: str, user_id: str, number: int) -> List[str]:
        urls = []

    async def get_user_avatar_url(self, post_id: str) -> List[str]:
        pass