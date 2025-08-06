from aiobotocore.session import get_session
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv()
POST_IMAGE_MAX_SIZE_MB = int(os.getenv("POST_IMAGE_MAX_SIZE_MB", "25"))
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "socialnetwork2025")

image_signatures = {
    b'\xFF\xD8\xFF': 'jpg',  # JPEG
    b'\x89PNG\r\n\x1a\n': 'png', # PNG
}

class S3Service:
    @staticmethod
    def validate_file_size(bytes_obj: bytes) -> bool:
        return 0 < len(bytes_obj) / 1024 / 1024 < POST_IMAGE_MAX_SIZE_MB
    
    @staticmethod
    def validate_image(bytes_obj: bytes) -> bool:
        pass
    
    @staticmethod
    def define_image_extension() -> str:
        pass

    @staticmethod
    def define_image_name(post_id: str, n_image: int):
        pass

    def __init__(self):
        self.session = get_session()

    @asynccontextmanager
    async def client(self):
        async with self.session("s3") as client:
            yield client
    
    async def upload_image(self, bytes_obj, post_id: str, n_image: int) -> None:
        """Use for uploading and image updating. \n S3 Has only PUT options."""
        pass

    async def delete_image(self, post_id: str, n_image: int) -> None:
        pass

    async def get_temp_image_url(self, post_id: str, n_image: int) -> str:
        pass