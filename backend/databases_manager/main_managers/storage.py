from fastapi import UploadFile
import magic
from abc import ABC, abstractmethod

from aiobotocore.session import get_session
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from typing import List, Literal


load_dotenv()
POST_IMAGE_MAX_SIZE_MB = int(os.getenv("POST_IMAGE_MAX_SIZE_MB", "25"))
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_BUCKET_NAME_TEST = os.getenv("S3_BUCKET_NAME_TEST")

ALLOWED_IMAGES_EXTENSIONS_MIME_RAW = os.getenv("ALLOWED_IMAGES_EXTENSIONS_MIME")
ALLOWED_EXTENSIONS = ALLOWED_IMAGES_EXTENSIONS_MIME_RAW.split(",")
for i, ext in enumerate(ALLOWED_EXTENSIONS):
    ALLOWED_EXTENSIONS[i] = ext.strip()

# ================================

class StorageABC(ABC):
    @abstractmethod
    def upload_image_post(self, contents: bytes, content_type: str, post_id: str, n_image: int):
        """
        Use for uploading and image updating. \n S3 Has only PUT options. \n
        N_image indicates number of image uploaded.
        """

    @abstractmethod
    async def upload_avatar_user(self, contents: bytes, extension: str, user_id: str) -> None:
        """Use for uploading and image updating. \n S3 Has only PUT options."""

    @abstractmethod
    async def delete_image_post(self, post_id: str, n_image: int) -> None:
        """Delete n's post image"""

    @abstractmethod
    async def delete_avatar_user(self, user_id: str, n_image: int) -> None:
        pass

    @abstractmethod
    async def get_temp_post_image_url(self, post_id: str, n_image: int) -> List[str]:
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
    
    async def upload_image_post(self, contents: bytes, mime_type: str, post_id: str, n_image: int) -> None:
        async with self._client() as s3:
            image_name = self._define_image_name(post_id=post_id, n_image=n_image)
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
            
    async def delete_image_post(self, post_id: str, n_image: int) -> None:
        async with self._client as s3:
            pass

    async def delete_avatar_user(self, user_id: str, n_image: int) -> None:
        async with self._client as s3:
            pass

    async def get_temp_post_image_url(self, post_id: str, n_image: int) -> List[str]:
        async with self._client as s3:
            pass

    async def get_user_avatar_url(self, post_id: str) -> List[str]:
        async with self._client as s3:
            pass


class LocalStorage(StorageABC):
    pass