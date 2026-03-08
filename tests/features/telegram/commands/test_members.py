import pytest
from unittest.mock import AsyncMock, MagicMock
from app.features.expenses.errors import ChatNotFound, NotMember
from app.features.telegram.commands.members import (
    handleJoin,
    handleListMembers,
    handleLeave,
)


def make_ctx(username="alice", chat_id=100, user_id=1, message_id=1):
    ctx = MagicMock()
    ctx.tg_chat_id = chat_id
    ctx.tg_user_id = user_id
    ctx.message_id = message_id
    ctx.username = username
    ctx.first_name = "Alice"
    ctx.last_name = None
    return ctx


def make_messenger():
    m = MagicMock()
    m.send_message = AsyncMock()
    return m


def make_svc():
    svc = MagicMock()
    svc.add_member = AsyncMock()
    svc.remove_member = AsyncMock()
    svc.get_members = AsyncMock()
    return svc


class TestHandleJoin:
    @pytest.mark.asyncio
    async def test_successful_join(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        await handleJoin(ctx, messenger, svc)
        svc.add_member.assert_called_once_with(
            ctx.tg_chat_id,
            ctx.tg_user_id,
            username=ctx.username,
            first_name=ctx.first_name,
            last_name=ctx.last_name,
        )
        msg = messenger.send_message.call_args[1]["text"]
        assert "alice" in msg and "joined" in msg

    @pytest.mark.asyncio
    async def test_join_sends_reply_to_message(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        await handleJoin(ctx, messenger, svc)
        call_kwargs = messenger.send_message.call_args[1]
        assert call_kwargs["reply_to_message_id"] == ctx.message_id

    @pytest.mark.asyncio
    async def test_domain_error_sends_error_message(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.add_member.side_effect = ChatNotFound()
        await handleJoin(ctx, messenger, svc)
        messenger.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_not_member_error(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.add_member.side_effect = NotMember()
        await handleJoin(ctx, messenger, svc)
        messenger.send_message.assert_called_once()


class TestHandleListMembers:
    @pytest.mark.asyncio
    async def test_with_members(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.get_members.return_value = ["alice", "bob", "charlie"]
        await handleListMembers(ctx, messenger, svc)
        msg = messenger.send_message.call_args[1]["text"]
        assert "alice" in msg
        assert "bob" in msg
        assert "charlie" in msg

    @pytest.mark.asyncio
    async def test_no_members(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.get_members.return_value = []
        await handleListMembers(ctx, messenger, svc)
        msg = messenger.send_message.call_args[1]["text"]
        assert "No members" in msg

    @pytest.mark.asyncio
    async def test_single_member(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.get_members.return_value = ["alice"]
        await handleListMembers(ctx, messenger, svc)
        msg = messenger.send_message.call_args[1]["text"]
        assert "alice" in msg

    @pytest.mark.asyncio
    async def test_sends_reply_to_message(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.get_members.return_value = ["alice"]
        await handleListMembers(ctx, messenger, svc)
        call_kwargs = messenger.send_message.call_args[1]
        assert call_kwargs["reply_to_message_id"] == ctx.message_id

    @pytest.mark.asyncio
    async def test_chat_not_found_error(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.get_members.side_effect = ChatNotFound()
        await handleListMembers(ctx, messenger, svc)
        messenger.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_members_listed_with_bullet_points(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.get_members.return_value = ["alice", "bob"]
        await handleListMembers(ctx, messenger, svc)
        msg = messenger.send_message.call_args[1]["text"]
        assert "•" in msg


class TestHandleLeave:
    @pytest.mark.asyncio
    async def test_successful_leave(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        await handleLeave(ctx, messenger, svc)
        svc.remove_member.assert_called_once_with(ctx.tg_chat_id, ctx.tg_user_id)
        msg = messenger.send_message.call_args[1]["text"]
        assert "alice" in msg and "left" in msg

    @pytest.mark.asyncio
    async def test_leave_sends_reply_to_message(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        await handleLeave(ctx, messenger, svc)
        call_kwargs = messenger.send_message.call_args[1]
        assert call_kwargs["reply_to_message_id"] == ctx.message_id

    @pytest.mark.asyncio
    async def test_not_member_error(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.remove_member.side_effect = NotMember()
        await handleLeave(ctx, messenger, svc)
        messenger.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_not_found_error(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.remove_member.side_effect = ChatNotFound()
        await handleLeave(ctx, messenger, svc)
        messenger.send_message.assert_called_once()
