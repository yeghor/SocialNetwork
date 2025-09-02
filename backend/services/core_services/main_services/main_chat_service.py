from services.core_services import MainServiceBase
from services.postgres_service.models import User
from exceptions.custom_exceptions import *
from exceptions.exceptions_handler import web_exceptions_raiser
from pydantic_schemas.pydantic_schemas_chat import ChatResponse

class MainChatService(MainServiceBase):
    @web_exceptions_raiser
    async def get_messages_and_token(user: User) -> ChatResponse:
        pass

    @web_exceptions_raiser
    async def delete_message():
        pass

    @web_exceptions_raiser
    async def change_message():
        pass