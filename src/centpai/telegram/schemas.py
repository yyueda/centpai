from pydantic import BaseModel, Field
from typing import List

class User(BaseModel):
    id: int
    is_bot: bool
    first_name: str
    last_name: str | None = None
    username: str | None = None

class Chat(BaseModel):
    id: int
    type: str

class MessageEntity(BaseModel):
    type: str
    offset: int
    length: int

class Message(BaseModel):
    message_id: int
    chat: Chat
    from_: User | None = Field(default=None, alias="from")
    text: str | None = None
    entities: List[MessageEntity] | None = None

class Update(BaseModel):
    update_id: int
    message: Message | None = None
