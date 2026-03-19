from decimal import Decimal

import pytest
from unittest.mock import AsyncMock, Mock

from app.core.errors import DomainError
from app.features.expenses.errors import NotMember, UserNotRegistered
from app.features.expenses.service import ExpensesService
from app.features.telegram.commands.expenses import (
    amount_split,
    check_split_rule,
    equal_split_selected_users,
    handleAddExpense,
    percentage_split,
)


@pytest.fixture
def ctx():
    m = Mock()
    m.tg_chat_id = 100
    m.tg_user_id = 200
    m.username = "alice"
    m.message_id = 1
    return m


@pytest.fixture
def messenger():
    m = Mock()
    m.send_message = AsyncMock()
    return m


@pytest.fixture
def svc(mocker):
    s = mocker.Mock(spec=ExpensesService)
    s.add_expense = AsyncMock(return_value=[])
    s.add_expense_selected_users = AsyncMock(return_value=[])
    return s


class TestCheckSplitRule:

    def test_routes_to_equal_split(self):
        result = check_split_rule(["@bob", "@carol"], Decimal("30"), "alice")
        assert result == {
            "bob": Decimal("10.00"),
            "carol": Decimal("10.00"),
            "alice": Decimal("10.00"),
        }

    def test_routes_to_percentage_split(self):
        result = check_split_rule(["@bob=60%", "@alice=40%"], Decimal("100"), "alice")
        assert result == {
            "bob": Decimal("60.00"),
            "alice": Decimal("40.00"),
        }

    def test_routes_to_amount_split(self):
        result = check_split_rule(["@bob=6", "@alice=4"], Decimal("10"), "alice")
        assert result == {
            "bob": Decimal("6.00"),
            "alice": Decimal("4.00"),
        }


class TestEqualSplitSelectedUsers:

    def test_equal_split_success(self):
        result = equal_split_selected_users(
            ["@bob", "@carol"], Decimal("10.00"), "alice"
        )
        assert result == {
            "bob": Decimal("10.00"),
            "carol": Decimal("10.00"),
            "alice": Decimal("10.00"),
        }

    @pytest.mark.parametrize(
        "inputs", [["@bob=", "@carol"], ["@bob", "@carol="], ["@bob=10", "@carol=10"]]
    )
    def test_raises_on_bad_format(self, inputs):
        with pytest.raises(ValueError, match="Invalid equal split format"):
            equal_split_selected_users(inputs, Decimal("10.00"), "alice")

    def test_raises_if_requester_included(self):
        with pytest.raises(
            ValueError, match="do not need to include your own username"
        ):
            equal_split_selected_users(["@bob", "@alice"], Decimal("10.00"), "alice")


class TestPercentageSplit:

    def test_percentage_split_success(self):
        result = percentage_split(["@bob=60%", "@alice=40%"], Decimal("100"), "alice")
        assert result == {
            "bob": Decimal("60.00"),
            "alice": Decimal("40.00"),
        }

    @pytest.mark.parametrize(
        "inputs",
        [["@bob=60", "@alice=40%"], ["@bob=60%", "@alice=40"], ["@bob=", "@alice=40%"]],
    )
    def test_raises_on_bad_format(self, inputs):
        with pytest.raises(ValueError, match="Invalid percentage split format"):
            percentage_split(inputs, Decimal("100"), "alice")

    def test_raises_on_invalid_value(self):
        with pytest.raises(ValueError, match="Invalid value"):
            percentage_split(["@bob=abc%", "@alice=40%"], Decimal("100"), "alice")

    def test_raises_if_percentages_not_100(self):
        with pytest.raises(ValueError, match="Invalid percentage splits"):
            percentage_split(["@bob=50%", "@alice=40%"], Decimal("100"), "alice")

    def test_raises_if_requester_not_included(self):
        with pytest.raises(ValueError, match="need to include your own username"):
            percentage_split(["@bob=100%"], Decimal("100"), "alice")


class TestAmountSplit:

    def test_amount_split_success(self):
        result = amount_split(["@bob=6", "@alice=4"], Decimal("10"), "alice")
        assert result == {
            "bob": Decimal("6.00"),
            "alice": Decimal("4.00"),
        }

    @pytest.mark.parametrize(
        "inputs",
        [
            ["@bob=", "@alice=4"],
            ["@bob=6", "@alice="],
            ["@bob", "@alice=4"],
            ["@bob=6", "@alice"],
        ],
    )
    def test_raises_on_bad_format(self, inputs):
        with pytest.raises(ValueError, match="Invalid amount split format"):
            amount_split(inputs, Decimal("10"), "alice")

    def test_raises_on_invalid_value(self):
        with pytest.raises(ValueError, match="Invalid value"):
            amount_split(["@bob=6%", "@alice=4"], Decimal("10"), "alice")

    def test_raises_if_amounts_dont_sum_to_total(self):
        with pytest.raises(ValueError, match="Invalid amount splits"):
            amount_split(["@bob=5", "@alice=4"], Decimal("10"), "alice")

    def test_raises_if_requester_not_included(self):
        with pytest.raises(ValueError, match="need to include your own username"):
            amount_split(["@bob=10"], Decimal("10"), "alice")


class TestHandleAddExpense:

    async def test_no_args_sends_usage(self, ctx, messenger, svc):
        await handleAddExpense(ctx, messenger, svc, args=[], mentioned_usernames=[])

        messenger.send_message.assert_called_once()
        call_text = messenger.send_message.call_args[0][1]
        assert "Usage" in call_text

    async def test_invalid_amount_sends_error(self, ctx, messenger, svc):
        await handleAddExpense(
            ctx, messenger, svc, args=["abc", "lunch"], mentioned_usernames=[]
        )

        messenger.send_message.assert_called_once()
        call_text = messenger.send_message.call_args[0][1]
        assert "input a valid amount" in call_text
        svc.add_expense.assert_not_called()
        svc.add_expense_selected_users.assert_not_called()

    async def test_no_mentions_calls_add_expense(self, ctx, messenger, svc):
        await handleAddExpense(
            ctx, messenger, svc, args=["10", "lunch"], mentioned_usernames=[]
        )

        svc.add_expense.assert_called_once_with(100, 200, Decimal("10.00"), "lunch")
        svc.add_expense_selected_users.assert_not_called()
        messenger.send_message.assert_called_once()
        call_text = messenger.send_message.call_args[1]["text"]
        assert "Expense added" in call_text

    async def test_equal_split_mentions_calls_add_expense_selected_users(
        self, ctx, messenger, svc
    ):
        await handleAddExpense(
            ctx,
            messenger,
            svc,
            args=["30", "dinner", "@bob", "@carol"],
            mentioned_usernames=["@bob", "@carol"],
        )

        svc.add_expense_selected_users.assert_called_once()
        svc.add_expense.assert_not_called()
        messenger.send_message.assert_called_once()
        call_text = messenger.send_message.call_args[1]["text"]
        assert "Expense added" in call_text

    async def test_percentage_split_calls_add_expense_selected_users(
        self, ctx, messenger, svc
    ):
        await handleAddExpense(
            ctx,
            messenger,
            svc,
            args=["100", "dinner", "@bob=60%", "@alice=40%"],
            mentioned_usernames=["@bob=60%", "@alice=40%"],
        )

        svc.add_expense_selected_users.assert_called_once()
        svc.add_expense.assert_not_called()
        messenger.send_message.assert_called_once()
        call_text = messenger.send_message.call_args[1]["text"]
        assert "Expense added" in call_text

    async def test_amount_split_calls_add_expense_selected_users(
        self, ctx, messenger, svc
    ):
        await handleAddExpense(
            ctx,
            messenger,
            svc,
            args=["10", "dinner", "@bob=6", "@alice=4"],
            mentioned_usernames=["@bob=6", "@alice=4"],
        )

        svc.add_expense_selected_users.assert_called_once()
        svc.add_expense.assert_not_called()
        messenger.send_message.assert_called_once()
        call_text = messenger.send_message.call_args[1]["text"]
        assert "Expense added" in call_text

    async def test_domain_error_sends_error_message(self, ctx, messenger, svc):
        svc.add_expense.side_effect = DomainError("Chat not found")

        await handleAddExpense(
            ctx, messenger, svc, args=["10", "lunch"], mentioned_usernames=[]
        )

        messenger.send_message.assert_called_once()
        call_text = messenger.send_message.call_args[0][1]
        assert call_text == "Chat not found"

    async def test_value_error_from_split_sends_error_message(
        self, ctx, messenger, svc
    ):
        # Percentages don't sum to 100 — triggers ValueError in split rule
        await handleAddExpense(
            ctx,
            messenger,
            svc,
            args=["100", "@bob=50%", "@alice=40%"],
            mentioned_usernames=["@bob=50%", "@alice=40%"],
        )

        messenger.send_message.assert_called_once()
        svc.add_expense_selected_users.assert_not_called()
