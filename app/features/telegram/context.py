from dataclasses import dataclass

from app.features.telegram.schemas import Update

@dataclass(frozen=True)
class TgContext:
    tg_chat_id: int
    tg_user_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    message_id: int | None
    text: str | None

def build_context_from_update(u: Update) -> TgContext:
    # if button is pressed
    # if u.callback_query:
    #     data = u.callback_query.data

    if u.message is None and u.my_chat_member is None:
        raise ValueError("Unsupported update")
    
     # Defaults for update types that don't carry message
    message_id: int | None = None
    text: str | None = None

    if u.message:
        msg = u.message
        chat = msg.chat
        user = msg.from_
        message_id = msg.message_id
        text = msg.text
    else:
        mcm = u.my_chat_member
        assert mcm is not None
        chat = mcm.chat
        user = mcm.from_

    return TgContext(
        tg_chat_id=chat.id,
        tg_user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        message_id=message_id,
        text=text
    )
