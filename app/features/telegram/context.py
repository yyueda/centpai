from dataclasses import dataclass

from app.features.telegram.schemas import Update


@dataclass(frozen=True)
class TgContext:
    tg_chat_id: int
    tg_user_id: int
    username: str
    first_name: str | None
    last_name: str | None
    message_id: int | None
    text: str | None


def build_context_from_update(u: Update) -> TgContext | None:
    # Defaults for update types that don't carry message
    message_id: int | None = None
    text: str | None = None

    if u.message:
        msg = u.message
        chat = msg.chat
        user = msg.from_
        message_id = msg.message_id
        text = msg.text
        # Username is compulsory
        if user.username is None:
            return None
    # Button clicks
    elif u.callback_query and u.callback_query.message:
        cq = u.callback_query
        chat = cq.message.chat
        user = cq.from_
        message_id = cq.message.message_id
        text = cq.data
    elif u.my_chat_member:
        mcm = u.my_chat_member
        chat = mcm.chat
        user = mcm.from_
    else:
        return None

    return TgContext(
        tg_chat_id=chat.id,
        tg_user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        message_id=message_id,
        text=text,
    )
