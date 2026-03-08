import pytest
from pydantic import ValidationError
from app.features.telegram.schemas import (
    User,
    Chat,
    MessageEntity,
    Message,
    ChatMember,
    ChatMemberUpdated,
    CallbackQuery,
    Update,
)


def make_user():
    return User(id=1, is_bot=False, first_name="Alice", username="alice")


def make_chat():
    return Chat(id=100, type="group")


def make_message():
    return Message(
        message_id=1,
        chat=make_chat(),
        **{"from": make_user()},
        text="hello",
    )


class TestUser:
    def test_valid(self):
        u = make_user()
        assert u.id == 1
        assert u.username == "alice"
        assert u.last_name is None

    def test_with_last_name(self):
        u = User(id=2, is_bot=False, first_name="Bob", last_name="Smith", username="bob")
        assert u.last_name == "Smith"

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            User(id=1, is_bot=False)  # missing first_name, username


class TestChat:
    def test_valid(self):
        c = make_chat()
        assert c.id == 100
        assert c.type == "group"

    def test_private_type(self):
        c = Chat(id=1, type="private")
        assert c.type == "private"


class TestMessageEntity:
    def test_basic(self):
        e = MessageEntity(type="bot_command", offset=0, length=5)
        assert e.type == "bot_command"
        assert e.user is None

    def test_with_user(self):
        u = make_user()
        e = MessageEntity(type="text_mention", offset=0, length=5, user=u)
        assert e.user.username == "alice"


class TestMessage:
    def test_valid(self):
        msg = make_message()
        assert msg.message_id == 1
        assert msg.text == "hello"

    def test_from_alias(self):
        # 'from' is a reserved word, must use alias
        msg = Message(
            message_id=1,
            chat=make_chat(),
            **{"from": make_user()},
        )
        assert msg.from_.username == "alice"

    def test_no_text(self):
        msg = Message(
            message_id=2,
            chat=make_chat(),
            **{"from": make_user()},
        )
        assert msg.text is None

    def test_with_entities(self):
        entities = [MessageEntity(type="bot_command", offset=0, length=5)]
        msg = Message(
            message_id=1,
            chat=make_chat(),
            **{"from": make_user()},
            text="/help",
            entities=entities,
        )
        assert len(msg.entities) == 1


class TestChatMember:
    def test_valid(self):
        cm = ChatMember(status="member")
        assert cm.status == "member"


class TestChatMemberUpdated:
    def test_valid(self):
        cmu = ChatMemberUpdated(
            chat=make_chat(),
            **{"from": make_user()},
            date=123456,
            old_chat_member=ChatMember(status="left"),
            new_chat_member=ChatMember(status="member"),
        )
        assert cmu.from_.username == "alice"
        assert cmu.new_chat_member.status == "member"


class TestCallbackQuery:
    def test_valid(self):
        cq = CallbackQuery(
            id="abc",
            **{"from": make_user()},
            message=make_message(),
            data="join_group",
        )
        assert cq.id == "abc"
        assert cq.data == "join_group"

    def test_no_data(self):
        cq = CallbackQuery(
            id="abc",
            **{"from": make_user()},
            message=make_message(),
        )
        assert cq.data is None


class TestUpdate:
    def test_only_update_id(self):
        u = Update(update_id=1)
        assert u.update_id == 1
        assert u.message is None
        assert u.callback_query is None
        assert u.my_chat_member is None

    def test_with_message(self):
        u = Update(update_id=1, message=make_message())
        assert u.message is not None

    def test_with_callback_query(self):
        cq = CallbackQuery(
            id="x", **{"from": make_user()}, message=make_message(), data="test"
        )
        u = Update(update_id=2, callback_query=cq)
        assert u.callback_query.data == "test"