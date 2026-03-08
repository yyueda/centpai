import pytest
from unittest.mock import AsyncMock, MagicMock
from app.features.telegram.commands.admin import handleHelp, handleInit, COMMANDS_TEXT


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
    return svc


class TestCommandsText:
    def test_contains_help(self):
        assert "/help" in COMMANDS_TEXT

    def test_contains_join(self):
        assert "/join" in COMMANDS_TEXT

    def test_contains_leave(self):
        assert "/leave" in COMMANDS_TEXT

    def test_contains_members(self):
        assert "/members" in COMMANDS_TEXT

    def test_contains_expense_add(self):
        assert "/expense_add" in COMMANDS_TEXT

    def test_contains_expense_view(self):
        assert "/expense_view" in COMMANDS_TEXT

    def test_contains_expense_remove(self):
        assert "/expense_remove" in COMMANDS_TEXT

    def test_contains_pay(self):
        assert "/pay" in COMMANDS_TEXT

    def test_contains_split_rules_section(self):
        assert "Split Rules" in COMMANDS_TEXT

    def test_contains_example_usage(self):
        assert "Example" in COMMANDS_TEXT


class TestHandleHelp:
    @pytest.mark.asyncio
    async def test_sends_commands_text(self):
        ctx, messenger = make_ctx(), make_messenger()
        await handleHelp(ctx, messenger)
        messenger.send_message.assert_called_once_with(ctx.tg_chat_id, COMMANDS_TEXT)

    @pytest.mark.asyncio
    async def test_sends_to_correct_chat(self):
        ctx, messenger = make_ctx(chat_id=999), make_messenger()
        await handleHelp(ctx, messenger)
        call_args = messenger.send_message.call_args[0]
        assert call_args[0] == 999

    @pytest.mark.asyncio
    async def test_sends_exactly_once(self):
        ctx, messenger = make_ctx(), make_messenger()
        await handleHelp(ctx, messenger)
        assert messenger.send_message.call_count == 1


class TestHandleInit:
    @pytest.mark.asyncio
    async def test_calls_add_member(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        await handleInit(ctx, messenger, svc)
        svc.add_member.assert_called_once_with(
            ctx.tg_chat_id,
            ctx.tg_user_id,
            username=ctx.username,
            first_name=ctx.first_name,
            last_name=ctx.last_name,
        )

    @pytest.mark.asyncio
    async def test_sends_welcome_message(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        await handleInit(ctx, messenger, svc)
        messenger.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_welcome_contains_inline_keyboard(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        await handleInit(ctx, messenger, svc)
        call_kwargs = messenger.send_message.call_args[1]
        assert "reply_markup" in call_kwargs
        assert "inline_keyboard" in call_kwargs["reply_markup"]

    @pytest.mark.asyncio
    async def test_welcome_keyboard_has_join_button(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        await handleInit(ctx, messenger, svc)
        keyboard = messenger.send_message.call_args[1]["reply_markup"][
            "inline_keyboard"
        ]
        flat_buttons = [btn for row in keyboard for btn in row]
        texts = [b["text"] for b in flat_buttons]
        assert any("Join" in t for t in texts)

    @pytest.mark.asyncio
    async def test_welcome_keyboard_has_leave_button(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        await handleInit(ctx, messenger, svc)
        keyboard = messenger.send_message.call_args[1]["reply_markup"][
            "inline_keyboard"
        ]
        flat_buttons = [btn for row in keyboard for btn in row]
        texts = [b["text"] for b in flat_buttons]
        assert any("Leave" in t for t in texts)

    @pytest.mark.asyncio
    async def test_welcome_keyboard_has_callback_data(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        await handleInit(ctx, messenger, svc)
        keyboard = messenger.send_message.call_args[1]["reply_markup"][
            "inline_keyboard"
        ]
        flat_buttons = [btn for row in keyboard for btn in row]
        assert all("callback_data" in b for b in flat_buttons)

    @pytest.mark.asyncio
    async def test_welcome_message_contains_commands(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        await handleInit(ctx, messenger, svc)
        text = messenger.send_message.call_args[1]["text"]
        assert "/join" in text or "Welcome" in text

    @pytest.mark.asyncio
    async def test_sends_to_correct_chat(self):
        ctx, messenger, svc = make_ctx(chat_id=555), make_messenger(), make_svc()
        await handleInit(ctx, messenger, svc)
        call_kwargs = messenger.send_message.call_args[1]
        assert call_kwargs["chat_id"] == 555
