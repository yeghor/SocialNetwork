from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
from pydantic_schemas.pydantic_schemas_social import UserShortSchemaAvatarURL

class HistoryMessage(BaseModel):
    message_id: str
    message: str
    date: datetime = Field(default=datetime.utcnow())
    owner: UserShortSchemaAvatarURL

class ChatResponse(BaseModel):
    messages: List[HistoryMessage]
    token: str
