from services.core_services import MainServiceBase
from services.postgres_service.models import *
from exceptions.custom_exceptions import *
from exceptions.exceptions_handler import web_exceptions_raiser
from pydantic_schemas.pydantic_schemas_chat import *
from post_popularity_rate_task.popularity_rate import scheduler
from uuid import uuid4

from services.redis_service import ChatType

from dotenv import load_dotenv
from os import getenv

load_dotenv()

MIN_CHAT_GROUP_PARTICIPANTS = int(getenv("MIN_CHAT_GROUP_PARTICIPANTS", 3))
MAX_CHAT_GROUP_PARTICIPANTS = int(getenv("MIN_CHAT_GROUP_PARTICIPANTS", 3))

class MainChatService(MainServiceBase):
    @staticmethod
    def _create_message(text: str, room_id: str, owner_id: str) -> Message:
        return Message(message_id=str(uuid4()), room_id=room_id, owner_id=owner_id, text=text)

    @staticmethod
    def _check_if_users_are_friends(user: User, other_user: User) -> bool:
        if user in other_user.followed and user in other_user.followers:
            return True
        else: 
            return False

    async def _get_and_authorize_chat_room(self, room_id: str, user_id: User, return_chat_room: bool = False) -> ChatRoom | None:
        chat_room = await self._PostgresService.get_chat_room(room_id=room_id)

        if not chat_room:
            raise ResourceNotFound(detail=f"ChatService: User: {user_id} tried to get messages from chat: {room_id} that does not exist.", client_safe_detail="Chat you're tring to access does not exist")
        
        if not user_id in [participant.user_id for participant in chat_room.participants]:
            raise Unauthorized(detail=f"ChatService: User: {user_id} tried to acces chat: {room_id} while not being it's participant.", client_safe_detail="Unauthorized")

        return chat_room if return_chat_room else None

    @web_exceptions_raiser
    async def execute_action(self, request_data: ExpectedWSData, connection_data: ChatJWTPayload) -> None:
        if request_data.action == "send":
            await self.send_message(message_data=request_data, request_data=connection_data)
        elif request_data.action == "change":
            await self.change_message(message_data=request_data, request_data=connection_data)
        elif request_data.action == "delete":
            await self.delete_message(message_data=request_data, request_data=connection_data)

    @web_exceptions_raiser
    async def get_chat_token(self, room_id: str, user: User) -> ChatTokenResponse:
        await self._get_and_authorize_chat_room(room_id=room_id, user_id=user, return_chat_room=False)
        return await self._JWT.generate_save_chat_token(room_id=room_id, user_id=user.user_id)

    @web_exceptions_raiser
    async def get_messages_batch(self, room_id: str, user: User, exclude: bool) -> List[HistoryMessage]:
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
    async def get_chat_batch(self, user: User, exclude: bool, chat_type: Literal["approved", "non-approved"]) -> List[Chat]:
        if exclude:
            exclude_ids = await self._RedisService.get_exclude_chat_ids(user_id=user.user_id, exclude_type=chat_type)
        else:
            await self._RedisService.clear_exclude_chat_ids(user_id=user.user_id, exclude_type=chat_type)
        
        chat_batch = await self._PostgresService.get_n_user_chats(user=user, exclude_ids=exclude_ids, chat_type=chat_type)

        await self._RedisService.add_exclude_chat_ids(
            exclude_ids=[chat.room_id for chat in chat_batch],
            user_id=user.user_id,
            exclude_type=chat_type
        )

        return chat_batch


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
    async def delete_message(self, message_data: ExpectedWSData, user_data: ChatJWTPayload) -> None:
        message = await self._PostgresService.get_message_by_id(message_id=message_data.message_id)

        if not message:
            raise ResourceNotFound(detail=f"ChatService: User{user_data.user_id} tried to delete message: {message_data.message_id} that doesn't exist.", client_safe_detail="Message that you're trying to delete doesn't exist")

        if not message.owner_id == user_data.user_id:
            raise Unauthorized(detail=f"ChatService: User: {user_data.user_id} tried to delete message: {message.message_id} while not being it's owner.", client_safe_detail="Unathorized")

        await self._PostgresService.delete_models_and_flush(message)

    @web_exceptions_raiser
    async def change_message(self, message_data: ExpectedWSData, user_data: ChatJWTPayload) -> None:
        message = await self._PostgresService.get_message_by_id(message_id=message_data.message_id)

        if not message:
            raise ResourceNotFound(detail=f"ChatService: User{user_data.user_id} tried to change message: {message_data.message_id} that doesn't exist.", client_safe_detail="Message that you're trying to delete doesn't exist")

        if not message.owner_id == user_data.user_id:
            raise Unauthorized(detail=f"ChatService: User: {user_data.user_id} tried to change message: {message.message_id} while not being it's owner.", client_safe_detail="Unathorized")

        await self._PostgresService.change_field_and_flush(model=message, text=message_data.message)

    @web_exceptions_raiser
    async def create_dialogue_chat(self, data: CreateDialoqueRoomBody, user: User) -> None:
        other_user = await self._PostgresService.get_user_by_id(data.other_participant_id)

        if other_user.user_id == user.user_id:
            raise InvalidAction(detail=f"ChatService: User: {user.user_id} tried to create dialogue chat with himself.", client_safe_detail="You can't create chat with yourself")

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
        
        chat_room_id = str(uuid4())

        chat_room = ChatRoom(room_id=chat_room_id, is_group=False, approved=False, participants=[user, other_user])
        message = self._create_message(text=data.message, room_id=chat_room_id, owner_id=user.user_id)

        await self._PostgresService.insert_models_and_flush(chat_room, message)



    @web_exceptions_raiser
    async def create_group_chat(self, data: CreateGroupRoomBody, user: User) -> None:
        # Adding one to include creator
        if not MIN_CHAT_GROUP_PARTICIPANTS <= len(data.other_participants_ids) + 1 <= MAX_CHAT_GROUP_PARTICIPANTS:
            raise InvalidResourceProvided(detail=f"ChatService: User: {user.user_id} triedt to create chat with {len(data.other_participants_ids)} participants, which isn't allowed.", client_safe_detail=f"You can't create group with more than {MAX_CHAT_GROUP_PARTICIPANTS} or fewer than {MIN_CHAT_GROUP_PARTICIPANTS} members")

        participants = await self._PostgresService.get_entries_by_ids(ids=data.other_participants_ids, ModelType=User)

        if not participants:
            raise ResourceNotFound(detail=f"ChatService: User: {user.user_id} tried to create group chat with some of participants that don't exist.", client_safe_detail="You're trying to create group with people that aren't exist")
        
        for participant in participants:
            if not self._check_if_users_are_friends(user=user, other_user=participant):
                raise InvalidResourceProvided(detail=f"ChatService: User: {user.user_id} tried to create group while not being friends with participant: {participant.user_id}", client_safe_detail=f"You can't create group while not being friend with members")
        
        if user in participants:
            raise InvalidResourceProvided(detail=f"ChatService: User {user.user_id} tried to create group with himself.", client_safe_detail="You can't create group with yourself")

        chat_room_id = str(uuid4())
        participants.append(user)

        chat_room = ChatRoom(room_id=chat_room_id, created=datetime.utcnow(), is_group=True, approved=True, participants=participants)
        message = self._create_message(text=data.message, room_id=chat_room_id, owner_id=user.user_id)

        await self._PostgresService.insert_models_and_flush(chat_room, message)

    @web_exceptions_raiser
    async def add_participant_to_group(self, room_id: str, participant_id: str, user: User) -> None:
        chat_room = await self._get_and_authorize_chat_room(room_id=room_id, user_id=user.user_id, return_chat_room=True)

        if len(chat_room.participants) >= MAX_CHAT_GROUP_PARTICIPANTS:
            raise InvalidAction(detail=f"ChatService: User: {user.user_id} tried to add participatn: {participant_id} to group: {room_id}, but reached maximum paritcipants limit.", client_safe_detail=f"You can't add more that {MAX_CHAT_GROUP_PARTICIPANTS} members to fgroup")
        
        new_participant = await self._PostgresService.get_user_by_id(user_id=participant_id)

        if new_participant.user_id == user.user_id:
            raise InvalidAction(detail=f"User: {user.user_id} tried to add himself to group: {room_id}")

        if new_participant in chat_room.participants:
            raise InvalidAction(detail=f"User: {user.user_id} tried to add participant: {participant_id} to group: {room_id} that that already participating in this group.")
        