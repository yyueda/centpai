import pytest
from app.features.telegram.commands.command_parser import (
    parse_command,
    Command,
    CommandName,
    _find_command_entity,
    _slice_entity_text,
    _slice_from_utf16_offset,
)
from app.features.telegram.schemas import Message, MessageEntity, Chat, User


def make_user(username="testuser"):
    return User(
        id=1, is_bot=False, first_name="Test", last_name=None, username=username
    )


def make_chat():
    return Chat(id=100, type="group")


def make_message(text, entities=None):
    return Message(
        message_id=1,
        chat=make_chat(),
        **{"from": make_user()},
        text=text,
        entities=entities,
    )


def make_command_entity(length, offset=0):
    return MessageEntity(type="bot_command", offset=offset, length=length)


class TestSliceEntityText:
    def test_basic_ascii(self):
        result = _slice_entity_text(
            "hello world", MessageEntity(type="x", offset=0, length=5)
        )
        assert result == "hello"

    def test_offset(self):
        result = _slice_entity_text(
            "/help me", MessageEntity(type="x", offset=0, length=5)
        )
        assert result == "/help"

    def test_unicode(self):
        text = "hi 😀 world"
        # '😀' is 2 UTF-16 code units
        entity = MessageEntity(type="x", offset=0, length=2)
        result = _slice_entity_text(text, entity)
        assert result == "hi"


class TestSliceFromUtf16Offset:
    def test_basic(self):
        result = _slice_from_utf16_offset("hello world", 6)
        assert result == "world"

    def test_zero_offset(self):
        result = _slice_from_utf16_offset("hello", 0)
        assert result == "hello"


class TestFindCommandEntity:
    def test_finds_command_at_offset_0(self):
        entities = [MessageEntity(type="bot_command", offset=0, length=5)]
        msg = make_message("/help", entities)
        result = _find_command_entity(msg)
        assert result is not None
        assert result.type == "bot_command"

    def test_ignores_command_not_at_offset_0(self):
        entities = [MessageEntity(type="bot_command", offset=3, length=5)]
        msg = make_message("hi /help", entities)
        result = _find_command_entity(msg)
        assert result is None

    def test_no_entities(self):
        msg = make_message("hello")
        result = _find_command_entity(msg)
        assert result is None

    def test_non_command_entity(self):
        entities = [MessageEntity(type="mention", offset=0, length=5)]
        msg = make_message("@user hello", entities)
        result = _find_command_entity(msg)
        assert result is None


class TestParseCommand:
    def test_returns_none_if_no_text(self):
        msg = make_message(None)
        assert parse_command(msg) is None

    def test_returns_none_if_no_entities(self):
        msg = make_message("/help")
        assert parse_command(msg) is None

    def test_returns_none_for_unknown_command(self):
        entities = [make_command_entity(length=8)]
        msg = make_message("/unknown", entities)
        assert parse_command(msg) is None

    def test_parse_help(self):
        entities = [make_command_entity(length=5)]
        msg = make_message("/help", entities)
        cmd = parse_command(msg)
        assert cmd is not None
        assert cmd.name == CommandName.HELP
        assert cmd.args == []

    def test_parse_join(self):
        entities = [make_command_entity(length=5)]
        msg = make_message("/join", entities)
        cmd = parse_command(msg)
        assert cmd.name == CommandName.JOIN

    def test_parse_leave(self):
        entities = [make_command_entity(length=6)]
        msg = make_message("/leave", entities)
        cmd = parse_command(msg)
        assert cmd.name == CommandName.LEAVE

    def test_parse_members(self):
        entities = [make_command_entity(length=8)]
        msg = make_message("/members", entities)
        cmd = parse_command(msg)
        assert cmd.name == CommandName.MEMBERS

    def test_parse_expense_add_with_args(self):
        entities = [make_command_entity(length=12)]
        msg = make_message("/expense_add Dinner 48.50", entities)
        cmd = parse_command(msg)
        assert cmd.name == CommandName.EXPENSE_ADD
        assert "Dinner" in cmd.args
        assert "48.50" in cmd.args

    def test_parse_expense_view(self):
        entities = [make_command_entity(length=13)]
        msg = make_message("/expense_view", entities)
        cmd = parse_command(msg)
        assert cmd.name == CommandName.EXPENSE_VIEW

    def test_parse_expense_remove(self):
        entities = [make_command_entity(length=15)]
        msg = make_message("/expense_remove 5", entities)
        cmd = parse_command(msg)
        assert cmd.name == CommandName.EXPENSE_REMOVE
        assert cmd.args == ["5"]

    def test_parse_pay_with_args(self):
        entities = [make_command_entity(length=4)]
        msg = make_message("/pay @alice 25", entities)
        cmd = parse_command(msg)
        assert cmd.name == CommandName.PAY

    def test_parse_debts(self):
        entities = [make_command_entity(length=6)]
        msg = make_message("/debts", entities)
        cmd = parse_command(msg)
        assert cmd.name == CommandName.DEBTS

    def test_strips_bot_mention_from_command(self):
        # /help@mybot should parse as /help
        entities = [make_command_entity(length=12)]
        msg = make_message("/help@mybot", entities)
        cmd = parse_command(msg)
        assert cmd.name == CommandName.HELP

    def test_mentioned_usernames_extracted(self):
        user_entity = MessageEntity(type="mention", offset=5, length=6)
        cmd_entity = make_command_entity(length=4)
        msg = make_message("/pay @alice 25", entities=[cmd_entity, user_entity])
        cmd = parse_command(msg)
        assert "alice" in cmd.mentioned_usernames

    def test_text_mention_extracted(self):
        mentioned_user = make_user(username="bob")
        user_entity = MessageEntity(
            type="text_mention", offset=5, length=3, user=mentioned_user
        )
        cmd_entity = make_command_entity(length=4)
        msg = make_message("/pay Bob 25", entities=[cmd_entity, user_entity])
        cmd = parse_command(msg)
        assert mentioned_user.id in cmd.mentioned_user_ids

    def test_args_text_is_rest_of_message(self):
        entities = [make_command_entity(length=12)]
        msg = make_message("/expense_add Dinner 48.50", entities)
        cmd = parse_command(msg)
        assert cmd.args_text == "Dinner 48.50"

    def test_empty_args(self):
        entities = [make_command_entity(length=5)]
        msg = make_message("/help", entities)
        cmd = parse_command(msg)
        assert cmd.args == []
        assert cmd.args_text == ""
