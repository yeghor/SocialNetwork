from json import load
from pydantic import BaseModel, Field, model_validator, field_validator
from typing import List, Literal, Any
from typing_extensions import Self
from datetime import datetime
from pydantic_schemas.pydantic_schemas_social import UserShortSchema
from exceptions.custom_exceptions import WSInvalidData, WSMessageIsTooBig
from services.postgres_service import User
from dotenv import load_dotenv
from os import getenv



ActionType = Literal["send", "change", "delete"]

load_dotenv()

MESSAGE_MAX_LEN = int(getenv("MESSAGE_MAX_LEN", "5000"))

class Chat(BaseModel):
    chat_id: str
    participants: int

class ActionIncluded(BaseModel):
    action: Literal["send", "change", "delete"] = "send"

class MessageSchemaShort(BaseModel):
    # Default value "send" for enabling model_validate with Message Postgre model
    
    message_id: str
    text: str | None = Field(default=None)

class MessageSchema(MessageSchemaShort):
    "Use in main http endpoints"
    text: str
    sent: datetime = Field(default=datetime.utcnow)
    owner: UserShortSchema

class MessageSchemaActionIncluded(MessageSchema, ActionIncluded):
    """Use in websockets 'send' action"""

class MessageSchemaShortActionIncluded(MessageSchemaShort, ActionIncluded):
    """Use in webosockets 'change' 'delete' actions"""



class ChatTokenResponse(BaseModel):
    token: str

    participants_avatar_urls: List[str]

class CreateChatBodyBase(BaseModel):
    message: str

class CreateDialoqueRoomBody(CreateChatBodyBase):
    other_participant_id: str

class CreateGroupRoomBody(CreateChatBodyBase):
    other_participants_ids: List[str]

class ExpectedWSData(BaseModel):
    action: ActionType

    message: str | None
    message_id: str | None

    @model_validator(mode="after")
    def validate_fields(self) -> Self:
        if self.action == "change":
            if not self.message or not self.message_id:
                raise WSInvalidData(f"Pydantic ExpectedWSData: The Schema received invalid data. Action - {self.action}. Message or it's id missing.")
        elif self.action == "delete":
            if not self.message_id:
                raise WSInvalidData("Pydantic ExpectedWSData: ExpectedWSData schema received invalid data.")
        else:
            if not self.message:
                raise WSInvalidData(f"Pydantic ExpectedWSData: The Schema received invalid data. Action - {self.action}. Message missing.")

        if self.message:
            if len(self.message) > MESSAGE_MAX_LEN:
                raise WSMessageIsTooBig(
                    detail=f"Pydantic ExpectedWSData: The schema received message that is too big. Length: {len(self.message)}.",
                    client_safe_detail=f"Message length can't be greater than 5000 chars"
                )

        return self
    
class ChatJWTPayload(BaseModel):
    room_id: str
    user_id: str