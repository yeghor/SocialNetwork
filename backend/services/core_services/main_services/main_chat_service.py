from services.core_services import MainServiceBase
from services.postgres_service.models import *
from exceptions.custom_exceptions import *
from exceptions.exceptions_handler import web_exceptions_raiser
from pydantic_schemas.pydantic_schemas_chat import *
from post_popularity_rate_task.popularity_rate import scheduler
from uuid import uuid4

class MainChatService(MainServiceBase):
    @web_exceptions_raiser
    async def get_chat_token(self, room_id: str, user: User) -> ChatTokenResponse:
        chatroom = await self._PostgresService.get_chat_room(room_id=room_id)

        if not user in chatroom.participants:
            raise Unauthorized(detail=f"ChatService: User: {user.user_id} tried to acces chat: {room_id} while not being it's participant.", client_safe_detail="Unauthorized")


    @web_exceptions_raiser
    async def get_chat_messages(self, room_id: str, user: User, exclude: bool) -> List[HistoryMessage]:
        pass

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
    async def get_chats(self, user: User, exclude: bool):
        pass

    @web_exceptions_raiser
    async def create_dialogue_chat(self, data: CreateDialoqueRoomBody, user: User):
        other_user = await self._PostgresService.get_user_by_id(data.other_participant_id)
        existing_dialogue = await self._PostgresService.get_dialogue_by_users(
            user_1=other_user,
            user_2=user
        )

        if existing_dialogue:
            if existing_dialogue.approved:
                detail=f"ChatService: User: {user.user_id} tried to create chat with user2: {data.other_participant_id} that already exist (approved).",
                client_safe_detail="Chat with this user already exist"
            else:
                detail = f"ChatService: User: {user.user_id} tried to create chat with user2: {data.other_participant_id} that already exists but is not yet approved.",
                client_safe_detail = "Chat with this user is pending for approval"

            raise Collision(
                detail=detail,
                client_safe_detail=client_safe_detail
            )
        
        chat_to_create = ChatRoom(room_id=str(uuid4()), is_group=False, approved=False)
        await self._PostgresService.insert_models_and_flush(chat_to_create)
        
        user.chat_rooms.append(chat_to_create)
        other_user.chat_rooms.append(chat_to_create)


        

    @web_exceptions_raiser
    async def create_group_chat(self, data: CreateGroupRoomBody, user: User):
        pass
