import pytest
from app.features.telegram.context import build_context_from_update, TgContext
from app.features.telegram.schemas import (
    Update,
    Message,
    Chat,
    User,
    CallbackQuery,
    ChatMemberUpdated,
    ChatMember,
)


def make_user(username="testuser", user_id=42):
    return User(
        id=user_id, is_bot=False, first_name="Test", last_name="User", username=username
    )


def make_chat(chat_id=100):
    return Chat(id=chat_id, type="group")


def make_message(text=None, user=None, chat=None, message_id=1):
    return Message(
        message_id=message_id,
        chat=chat or make_chat(),
        **{"from": user or make_user()},
        text=text,
    )


class TestBuildContextFromUpdate:
    def test_message_update(self):
        update = Update(
            update_id=1,
            message=make_message(text="/help"),
        )
        ctx = build_context_from_update(update)
        assert ctx is not None
        assert ctx.tg_chat_id == 100
        assert ctx.tg_user_id == 42
        assert ctx.username == "testuser"
        assert ctx.text == "/help"
        assert ctx.message_id == 1

    def test_message_without_username_returns_none(self):
        # The schema requires username as a string, so we mock the user object
        # to simulate a user with no username at the context-building level
        from unittest.mock import MagicMock, patch

        mock_user = MagicMock()
        mock_user.username = None
        mock_user.id = 1
        mock_user.first_name = "Test"
        mock_user.last_name = None

        msg = MagicMock()
        msg.chat.id = 100
        msg.from_ = mock_user
        msg.message_id = 1
        msg.text = "hello"

        update = MagicMock()
        update.message = msg
        update.callback_query = None
        update.my_chat_member = None

        ctx = build_context_from_update(update)
        assert ctx is None

    def test_callback_query_update(self):
        cq = CallbackQuery(
            id="cq1",
            **{"from": make_user(username="alice", user_id=99)},
            message=make_message(chat=make_chat(chat_id=200), message_id=5),
            data="join_group",
        )
        update = Update(update_id=2, callback_query=cq)
        ctx = build_context_from_update(update)
        assert ctx is not None
        assert ctx.tg_chat_id == 200
        assert ctx.tg_user_id == 99
        assert ctx.username == "alice"
        assert ctx.text == "join_group"
        assert ctx.message_id == 5

    def test_my_chat_member_update(self):
        mcm = ChatMemberUpdated(
            chat=make_chat(chat_id=300),
            **{"from": make_user(username="bob", user_id=77)},
            date=1234567890,
            old_chat_member=ChatMember(status="left"),
            new_chat_member=ChatMember(status="member"),
        )
        update = Update(update_id=3, my_chat_member=mcm)
        ctx = build_context_from_update(update)
        assert ctx is not None
        assert ctx.tg_chat_id == 300
        assert ctx.tg_user_id == 77
        assert ctx.username == "bob"

    def test_empty_update_returns_none(self):
        update = Update(update_id=99)
        ctx = build_context_from_update(update)
        assert ctx is None

    def test_context_is_immutable(self):
        update = Update(update_id=1, message=make_message(text="/help"))
        ctx = build_context_from_update(update)
        assert ctx is not None
        with pytest.raises(Exception):
            ctx.username = "hacker"  # type: ignore

    def test_first_name_and_last_name_propagated(self):
        user = User(
            id=10, is_bot=False, first_name="John", last_name="Doe", username="johndoe"
        )
        update = Update(update_id=1, message=make_message(user=user))
        ctx = build_context_from_update(update)
        assert ctx.first_name == "John"
        assert ctx.last_name == "Doe"

    def test_message_id_is_none_for_my_chat_member(self):
        mcm = ChatMemberUpdated(
            chat=make_chat(),
            **{"from": make_user()},
            date=123,
            old_chat_member=ChatMember(status="left"),
            new_chat_member=ChatMember(status="member"),
        )
        update = Update(update_id=1, my_chat_member=mcm)
        ctx = build_context_from_update(update)
        assert ctx.message_id is None
