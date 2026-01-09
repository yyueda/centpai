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
    user: User | None = None

class Message(BaseModel):
    message_id: int
    chat: Chat
    from_: User = Field(alias="from")
    text: str | None = None
    entities: List[MessageEntity] | None = None

class ChatMember(BaseModel):
    status: str

class ChatMemberUpdated(BaseModel):
    chat: Chat
    from_: User = Field(alias="from")
    date: int
    old_chat_member: ChatMember
    new_chat_member: ChatMember

class CallbackQuery(BaseModel):
    id: str
    from_: User = Field(alias="from")
    message: Message | None = None
    data: str | None = None

class Update(BaseModel):
    update_id: int
    message: Message | None = None
    my_chat_member: ChatMemberUpdated | None = None
    callback_query: CallbackQuery | None = None
