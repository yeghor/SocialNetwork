from main_managers.services_creator_abstractions import MainServiceBase

class MainMediaService(MainServiceBase):
    async def upload_user_avatar(self, avatar_contents: bytes, avatar_mime_type: str, user_id: str):
        if avatar_contents and avatar_mime_type:
            await self._ImageStorage.upload_avatar_user(contents=avatar_contents, mime_type=avatar_mime_type, user_id=user_id)

    async def upload_post_images():
        pass

    """..."""