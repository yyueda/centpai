from dataclasses import dataclass

@dataclass(frozen=True)
class TgContext:
    tg_chat_id: int
    tg_user_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    message_id: int
    text: str | None
