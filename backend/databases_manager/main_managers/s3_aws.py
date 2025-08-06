from fastapi import UploadFile

from aiobotocore.session import get_session
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from typing import List, Literal

load_dotenv()
POST_IMAGE_MAX_SIZE_MB = int(os.getenv("POST_IMAGE_MAX_SIZE_MB", "25"))
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_BUCKET_NAME_TEST = os.getenv("S3_BUCKET_NAME_TEST")


class S3Service:
    @staticmethod
    def _define_image_name(post_id: str, n_image: int):
        pass

    def __init__(self, mode: Literal["prod", "test"]):
        self._session = get_session()

        if mode == "prod": self._bucket_name = S3_BUCKET_NAME
        elif mode == "test": self._bucket_name = S3_BUCKET_NAME_TEST

    @asynccontextmanager
    async def _client(self):
        async with self._session("s3") as client:
            yield client
    
    async def upload_image_post(self, contents: bytes, extension, post_id: str, n_image: int) -> None:
        """Use for uploading and image updating. \n S3 Has only PUT options."""
        async with self._client as s3:
            for i in n_image:
                self._define_image_name
                pass

    async def upload_avatar_user(self, contents: bytes, extension, user_id: str) -> None:
        """Use for uploading and image updating. \n S3 Has only PUT options."""
        async with self._client as s3:
            pass
            
    async def delete_image_post(self, post_id: str, n_image: int) -> None:
        async with self._client as s3:
            pass

    async def delete_avatar_user(self, user_id: str, n_image: int) -> None:
        async with self._client as s3:
            pass

    async def get_temp_post_image_urls(self, post_id: str, n_image: int) -> List[str]:
        async with self._client as s3:
            pass

    async def get_user_avatar_urls(self, post_id: str, n_image: int) -> List[str]:
        async with self._client as s3:
            pass