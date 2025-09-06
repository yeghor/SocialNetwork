from services.core_services import MainServiceBase
from services.postgres_service.models import *
from exceptions.custom_exceptions import *
from exceptions.exceptions_handler import web_exceptions_raiser
from pydantic_schemas.pydantic_schemas_chat import *
from post_popularity_rate_task.popularity_rate import scheduler
from uuid import uuid4

class MainChatService(MainServiceBase):
    async def _get_and_authorize_chat_room(self, room_id: str, user_id: User, return_chat_room: bool = False) -> ChatRoom | None:
        chat_room = await self._PostgresService.get_chat_room(room_id=room_id)

        if not chat_room:
            raise ResourceNotFound(detail=f"ChatService: User: {user_id} tried to get messages from chat: {room_id} that does not exist.", client_safe_detail="Chat you're tring to access does not exist")
        
        if not user_id in [participant.user_id for participant in chat_room.participants]:
            raise Unauthorized(detail=f"ChatService: User: {user_id} tried to acces chat: {room_id} while not being it's participant.", client_safe_detail="Unauthorized")

        return chat_room if return_chat_room else None

    @web_exceptions_raiser
    async def get_chat_token(self, room_id: str, user: User) -> ChatTokenResponse:
        await self._get_and_authorize_chat_room(room_id=room_id, user_id=user, return_chat_room=False)
        return await self._JWT.generate_save_chat_token(room_id=room_id, user_id=user.user_id)

    @web_exceptions_raiser
    async def get_batch_chat_messages(self, room_id: str, user: User, exclude: bool) -> List[HistoryMessage]:
        await self._get_and_authorize_chat_room(room_id=room_id, user_id=user, return_chat_room=False)

        if exclude:
            exclude_ids = self._RedisService.get_exclude_chat_ids(user_id=user.user_id, exclude_type="message")
        else:
            await self._RedisService.clear_exclude_chat_ids(user_id=user.user_id, exclude_type="message")
            exclude_ids = []

        message_batch = await self._PostgresService.get_chat_n_fresh_chat_messages(room_id=room_id, exclude_ids=exclude_ids)

        await self._RedisService.add_exclude_chat_ids(
            exclude_ids=[message.message_id for message in message_batch],
            user_id=user.user_id,
            exclude_type="message"
        )

        return message_batch
        

    @web_exceptions_raiser
    async def approve_chat(self, room_id: str, user: User) -> None:
        chat_room = await self._get_and_authorize_chat_room(room_id=room_id, user_id=user, return_chat_room=True)

        if chat_room.approved:
            raise InvalidAction(detail=f"ChatService: User: {user.user_id} tried to approve dialogue chat: {room_id} that already approved.", client_safe_detail="You're already approved this chat")

        chat_room.approved = True
    
    @web_exceptions_raiser
    async def disapprove_chat(self, room_id: str, user: User) -> None:
        chat_room = await self._get_and_authorize_chat_room(room_id=room_id, user_id=user, return_chat_room=True)

        if chat_room.approved:
            raise InvalidAction(detail=f"ChatService: User: {user.user_id} tried to disapprove dialogue chat: {room_id} that already approved.", client_safe_detail="You're already approved this chat")

        await self._PostgresService.delete_models_and_flush(chat_room)

    @web_exceptions_raiser
    async def disconnect(self, user: User) -> None:
        """Necessarily call this methods when error occured or user disconnected from websocket to clear all excluding."""
        await self._RedisService.clear_exclude_chat_ids(user_id=user.user_id, exclude_type="message")

    @web_exceptions_raiser
    async def send_message(self, message_data: ExpectedWSData, user_data: ChatJWTPayload):
        await self._get_and_authorize_chat_room(room_id=user_data.room_id, user_id=user_data.user_id, return_chat_room=False)

        new_message = Message(message_id=str(uuid4()), room_id=user_data.room_id, owner_id=user_data.user_id, text=message_data.message)
        
        await self._PostgresService.insert_models_and_flush(new_message)

    @web_exceptions_raiser
    async def delete_message(self, ):
        pass

    @web_exceptions_raiser
    async def change_message(self, ):
        pass

    @web_exceptions_raiser
    async def create_dialogue_chat():
        pass

    @web_exceptions_raiser
    async def create_dialogue_chat(self, data: CreateDialoqueRoomBody, user: User) -> None:
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
