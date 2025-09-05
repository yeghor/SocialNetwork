from services.core_services import MainServiceBase
from services.postgres_service.models import User
from exceptions.custom_exceptions import *
from exceptions.exceptions_handler import web_exceptions_raiser
from pydantic_schemas.pydantic_schemas_chat import ChatResponse



class MainChatService(MainServiceBase):
    @web_exceptions_raiser
    async def get_messages_and_token(self, room_id: str, user: User) -> ChatResponse:
        chatroom = await self._PostgresService.get_chat_room(room_id=room_id)

        if not user in chatroom.participants:
            raise Unauthorized(detail=f"ChatService: User: {user.user_id} tried to acces chat: {room_id} while not being it's participant.", client_safe_detail="Unauthorized")

        messages = await self._PostgresService.get_chat_n_messages(room_id=room_id)

    @web_exceptions_raiser
    async def disconnect(self, user: User) -> None:
        """Necessarily call this methods when error occured or user disconnected from websocket to clear all excluding."""

    @web_exceptions_raiser
    async def send_message(self, ):
        pass

    @web_exceptions_raiser
    async def delete_message(self, ):
        pass

    @web_exceptions_raiser
    async def change_message(self, ):
        pass

    @web_exceptions_raiser
    async def get_chats(self, ):
        pass

    @web_exceptions_raiser
    async def create_dialogue_chat(self, ):
        pass

    @web_exceptions_raiser
    async def create_group_chat(self, ):
        pass
