from dataclasses import dataclass
from typing import List

from centpai.telegram.schemas import Message, MessageEntity

@dataclass
class Command:
    name: str
    args: List[str]
    args_text: str
    mentioned_user_ids: List[int]
    mentioned_usernames: List[str]

def _find_command_entity(message: Message) -> MessageEntity | None:
    """Find the bot_command entity that starts at the beginning of the message."""
    if not message.entities:
        return None
    for e in message.entities:
        if e.type == "bot_command" and e.offset == 0:
            return e
    return None

def _slice_entity_text(text: str, entity: MessageEntity) -> str:
    """Return the substring of `text` covered by this entity."""
    utf16 = text.encode("utf-16-le")
    start = entity.offset * 2
    end = (entity.offset + entity.length) * 2
    return utf16[start:end].decode("utf-16-le")

def _slice_from_utf16_offset(text: str, utf16_offset: int) -> str:
    """Return the substring of `text` starting at a UTF-16 code unit offset."""
    utf16 = text.encode("utf-16-le")
    start = utf16_offset * 2
    return utf16[start:].decode("utf-16-le")

def parse_command(message: Message) -> Command | None:
    if not message.text:
        return None

    text = message.text
    entities = message.entities or []

    cmd_entity = _find_command_entity(message)
    if not cmd_entity:
        return None

    raw_cmd = _slice_entity_text(text, cmd_entity)
    name = raw_cmd.lstrip("/")

    args_utf16_offset = cmd_entity.offset + cmd_entity.length
    raw_args = _slice_from_utf16_offset(text, args_utf16_offset).lstrip()
    args = raw_args.split() if raw_args else []

    mentioned_user_ids: List[int] = []
    mentioned_usernames: List[str] = []

    for e in entities:
        if e is cmd_entity:
            continue

        if e.type == "text_mention" and e.user:
            mentioned_user_ids.append(e.user.id)
        elif e.type == "mention":
            username = _slice_entity_text(text, e).lstrip("@")
            mentioned_usernames.append(username)

    return Command(
        name=name,
        args=args,
        args_text=raw_args,
        mentioned_user_ids=mentioned_user_ids,
        mentioned_usernames=mentioned_usernames
    )
