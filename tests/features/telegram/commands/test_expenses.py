import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from app.features.telegram.commands.expenses import (
    handleAddExpense,
    handleListExpenses,
    handleRemoveExpense,
    handlePay,
    handleDebts,
    parse_amount,
    parse_id,
    parse_user,
)
from app.features.expenses.dto import (
    BalanceDTO,
    ExpenseDTO,
    ExpenseParticipantDTO,
    SimplifiedDebtDTO,
)
from app.features.expenses.errors import (
    ChatNotFound,
    NotMember,
    ExpenseNotFoundError,
)
from datetime import datetime


def make_ctx(chat_id=100, user_id=1, message_id=1, username="alice"):
    ctx = MagicMock()
    ctx.tg_chat_id = chat_id
    ctx.tg_user_id = user_id
    ctx.message_id = message_id
    ctx.username = username
    return ctx


def make_messenger():
    m = MagicMock()
    m.send_message = AsyncMock()
    return m


def make_svc():
    svc = MagicMock()
    svc.add_expense = AsyncMock()
    svc.get_expenses = AsyncMock()
    svc.get_balances = AsyncMock()
    svc.remove_expense = AsyncMock()
    svc.process_payment = AsyncMock()
    svc.get_simplified_debts = AsyncMock()
    return svc


# ---- parse helpers ----


class TestParseAmount:
    def test_valid_integer(self):
        assert parse_amount("10") == Decimal("10.00")

    def test_valid_decimal(self):
        assert parse_amount("48.50") == Decimal("48.50")

    def test_rounds_to_two_dp(self):
        result = parse_amount("1.005")
        assert result == Decimal("1.01")  # ROUND_HALF_UP

    def test_invalid_raises_value_error(self):
        with pytest.raises(ValueError):
            parse_amount("abc")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            parse_amount("")


class TestParseId:
    def test_valid(self):
        assert parse_id("5") == 5

    def test_zero_raises(self):
        with pytest.raises(ValueError):
            parse_id("0")

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            parse_id("-1")

    def test_non_integer_raises(self):
        with pytest.raises(ValueError):
            parse_id("abc")


class TestParseUser:
    def test_valid(self):
        assert parse_user("@alice") == "alice"

    def test_missing_at_raises(self):
        with pytest.raises(ValueError):
            parse_user("alice")

    def test_extra_at_raises(self):
        with pytest.raises(ValueError):
            parse_user("extra@alice")


# ---- handler tests ----


class TestHandleAddExpense:
    @pytest.mark.asyncio
    async def test_no_args_sends_usage(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        await handleAddExpense(ctx, messenger, svc, [], [])
        messenger.send_message.assert_called_once()
        assert "Usage" in messenger.send_message.call_args[0][1]

    @pytest.mark.asyncio
    async def test_valid_expense_sends_balances(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.add_expense.return_value = [
            BalanceDTO(username="alice", balance=Decimal("10.00")),
            BalanceDTO(username="bob", balance=Decimal("-10.00")),
        ]
        await handleAddExpense(ctx, messenger, svc, ["48.50", "Dinner"], [])
        messenger.send_message.assert_called_once()
        msg = messenger.send_message.call_args[1]["text"]
        assert "alice" in msg or "bob" in msg

    @pytest.mark.asyncio
    async def test_invalid_amount_sends_error(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        await handleAddExpense(ctx, messenger, svc, ["notanumber"], [])
        messenger.send_message.assert_called_once()
        assert "valid amount" in messenger.send_message.call_args[0][1]

    @pytest.mark.asyncio
    async def test_domain_error_sends_message(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.add_expense.side_effect = ChatNotFound()
        await handleAddExpense(ctx, messenger, svc, ["10.00", "Lunch"], [])
        messenger.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_zero_balance_users_skipped(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.add_expense.return_value = [
            BalanceDTO(username="alice", balance=Decimal("0.00")),
            BalanceDTO(username="bob", balance=Decimal("-10.00")),
        ]
        await handleAddExpense(ctx, messenger, svc, ["10.00", "Lunch"], [])
        msg = messenger.send_message.call_args[1]["text"]
        assert "alice" not in msg


class TestHandleListExpenses:
    @pytest.mark.asyncio
    async def test_no_expenses(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.get_expenses.return_value = []
        svc.get_balances.return_value = []
        await handleListExpenses(ctx, messenger, svc)
        messenger.send_message.assert_called_once()
        assert "No expenses" in messenger.send_message.call_args[1]["text"]

    @pytest.mark.asyncio
    async def test_with_expenses(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.get_expenses.return_value = [
            ExpenseDTO(
                id=1,
                paid_by="alice",
                amount=Decimal("50.00"),
                desc="Dinner",
                created_at=datetime.now(),
                participants=[
                    ExpenseParticipantDTO(username="bob", amount_owed=Decimal("25.00"))
                ],
            )
        ]
        svc.get_balances.return_value = [
            BalanceDTO(username="bob", balance=Decimal("-25.00"))
        ]
        await handleListExpenses(ctx, messenger, svc)
        messenger.send_message.assert_called_once()
        msg = messenger.send_message.call_args[1]["text"]
        assert "alice" in msg

    @pytest.mark.asyncio
    async def test_domain_error(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.get_expenses.side_effect = ChatNotFound()
        await handleListExpenses(ctx, messenger, svc)
        messenger.send_message.assert_called_once()


class TestHandleRemoveExpense:
    @pytest.mark.asyncio
    async def test_no_args_sends_usage(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        await handleRemoveExpense(ctx, messenger, svc, [])
        assert "Usage" in messenger.send_message.call_args[0][1]

    @pytest.mark.asyncio
    async def test_valid_removal(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.remove_expense.return_value = None
        await handleRemoveExpense(ctx, messenger, svc, ["5"])
        msg = messenger.send_message.call_args[1]["text"]
        assert "5" in msg and "removed" in msg

    @pytest.mark.asyncio
    async def test_invalid_id_sends_error(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        await handleRemoveExpense(ctx, messenger, svc, ["abc"])
        messenger.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_domain_error(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.remove_expense.side_effect = ExpenseNotFoundError(5)
        await handleRemoveExpense(ctx, messenger, svc, ["5"])
        messenger.send_message.assert_called_once()


class TestHandlePay:
    @pytest.mark.asyncio
    async def test_no_args_sends_usage(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        await handlePay(ctx, messenger, svc, [])
        assert "Usage" in messenger.send_message.call_args[0][1]

    @pytest.mark.asyncio
    async def test_wrong_arg_count_sends_usage(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        await handlePay(ctx, messenger, svc, ["@bob"])
        assert "Usage" in messenger.send_message.call_args[0][1]

    @pytest.mark.asyncio
    async def test_valid_payment(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        await handlePay(ctx, messenger, svc, ["@bob", "25.00"])
        msg = messenger.send_message.call_args[1]["text"]
        assert "25" in msg and "bob" in msg

    @pytest.mark.asyncio
    async def test_invalid_username_format(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        await handlePay(ctx, messenger, svc, ["bob", "25.00"])
        messenger.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_domain_error(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.process_payment.side_effect = NotMember()
        await handlePay(ctx, messenger, svc, ["@bob", "10.00"])
        messenger.send_message.assert_called_once()


class TestHandleDebts:
    @pytest.mark.asyncio
    async def test_with_debts(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.get_simplified_debts.return_value = [
            SimplifiedDebtDTO(from_user="alice", to_user="bob", amount=Decimal("10.00"))
        ]
        await handleDebts(ctx, messenger, svc, [])
        msg = messenger.send_message.call_args[1]["text"]
        assert "alice" in msg
        assert "bob" in msg

    @pytest.mark.asyncio
    async def test_no_debts(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.get_simplified_debts.return_value = []
        await handleDebts(ctx, messenger, svc, [])
        messenger.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_domain_error(self):
        ctx, messenger, svc = make_ctx(), make_messenger(), make_svc()
        svc.get_simplified_debts.side_effect = ChatNotFound()
        await handleDebts(ctx, messenger, svc, [])
        messenger.send_message.assert_called_once()
