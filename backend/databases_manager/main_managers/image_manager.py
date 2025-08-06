import os
from dotenv import load_dotenv

load_dotenv()
POST_IMAGE_MAX_SIZE_MB = int(os.getenv("POST_IMAGE_MAX_SIZE_MB"))


class ImageService:
    @staticmethod
    def _validate_file_size(bytes_obj: bytes) -> bool:
        return 0 < len(bytes_obj) / 1024 / 1024 < POST_IMAGE_MAX_SIZE_MB
    
    @staticmethod
    def _validate_content_type(content_type: str) -> bool:
        pass

    @classmethod
    def validate_image(cls, content_type, readed_data: bytes) -> bool:
        return cls._validate_content_type(content_type=content_type) and cls._validate_file_size(bytes_obj=readed_data)