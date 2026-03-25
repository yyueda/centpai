from decimal import Decimal

import pytest
from unittest.mock import AsyncMock, Mock

from app.core.errors import DomainError
from app.features.expenses.dto import SplitRule
from app.features.expenses.service import ExpensesService
from app.features.telegram.commands.expenses import (
    check_split_rule,
    handleAddExpense,
)

_equal = ExpensesService._equal_split_selected_users
_percentage = ExpensesService._percentage_split
_amount = ExpensesService._amount_split


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
        result = check_split_rule(["@bob", "@carol"])
        assert result == SplitRule.EQUAL_SELECTED

    def test_routes_to_percentage_split(self):
        result = check_split_rule(["@bob=60%", "@alice=40%"])
        assert result == SplitRule.PERCENTAGE

    def test_routes_to_amount_split(self):
        result = check_split_rule(["@bob=6", "@alice=4"])
        assert result == SplitRule.AMOUNT


class TestEqualSplitSelectedUsers:

    def test_equal_split_success(self):
        # total $30 split 3 ways → $10 each
        result = _equal(["@bob", "@carol"], Decimal("30.00"), "alice")
        assert result == {
            "bob": Decimal("10.00"),
            "carol": Decimal("10.00"),
            "alice": Decimal("10.00"),
        }

    def test_equal_split_remainder_goes_to_mentioned_users(self):
        # $10 / 3 = $3.33 base; 1 remainder cent → bob gets $3.34
        result = _equal(["@bob", "@carol"], Decimal("10.00"), "alice")
        assert result == {
            "bob": Decimal("3.34"),
            "carol": Decimal("3.33"),
            "alice": Decimal("3.33"),
        }
        assert sum(result.values()) == Decimal("10.00")

    @pytest.mark.parametrize(
        "inputs", [["@bob=", "@carol"], ["@bob", "@carol="], ["@bob=10", "@carol=10"]]
    )
    def test_raises_on_bad_format(self, inputs):
        with pytest.raises(ValueError, match="Invalid equal split format"):
            _equal(inputs, Decimal("10.00"), "alice")

    def test_raises_if_requester_included(self):
        with pytest.raises(
            ValueError, match="do not need to include your own username"
        ):
            _equal(["@bob", "@alice"], Decimal("10.00"), "alice")


class TestPercentageSplit:

    def test_percentage_split_success(self):
        result = _percentage(["@bob=60%", "@alice=40%"], Decimal("100"), "alice")
        assert result == {
            "bob": Decimal("60.00"),
            "alice": Decimal("40.00"),
        }

    def test_percentage_split_remainder_absorbed_by_last_user(self):
        # 33.33% of $100 = $33.33 each for first two; last gets 100 - 66.66 = 33.34
        result = _percentage(
            ["@bob=33.33%", "@carol=33.33%", "@alice=33.34%"], Decimal("100"), "alice"
        )
        assert sum(result.values()) == Decimal("100.00")

    @pytest.mark.parametrize(
        "inputs",
        [["@bob=60", "@alice=40%"], ["@bob=60%", "@alice=40"], ["@bob=", "@alice=40%"]],
    )
    def test_raises_on_bad_format(self, inputs):
        with pytest.raises(ValueError, match="Invalid percentage split format"):
            _percentage(inputs, Decimal("100"), "alice")

    def test_raises_on_invalid_value(self):
        with pytest.raises(ValueError, match="Invalid value"):
            _percentage(["@bob=abc%", "@alice=40%"], Decimal("100"), "alice")

    def test_raises_if_percentages_not_100(self):
        with pytest.raises(ValueError, match="Invalid percentage splits"):
            _percentage(["@bob=50%", "@alice=40%"], Decimal("100"), "alice")

    def test_raises_if_requester_not_included(self):
        with pytest.raises(ValueError, match="need to include your own username"):
            _percentage(["@bob=100%"], Decimal("100"), "alice")


class TestAmountSplit:

    def test_amount_split_success(self):
        result = _amount(["@bob=6", "@alice=4"], Decimal("10"), "alice")
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
            _amount(inputs, Decimal("10"), "alice")

    def test_raises_on_invalid_value(self):
        with pytest.raises(ValueError, match="Invalid value"):
            _amount(["@bob=6%", "@alice=4"], Decimal("10"), "alice")

    def test_raises_if_amounts_dont_sum_to_total(self):
        with pytest.raises(ValueError, match="Invalid amount splits"):
            _amount(["@bob=5", "@alice=4"], Decimal("10"), "alice")

    def test_raises_if_requester_not_included(self):
        with pytest.raises(ValueError, match="need to include your own username"):
            _amount(["@bob=10"], Decimal("10"), "alice")


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
        # Percentages don't sum to 100 — service raises ValueError during parsing
        svc.add_expense_selected_users.side_effect = ValueError(
            "Invalid percentage splits."
        )

        await handleAddExpense(
            ctx,
            messenger,
            svc,
            args=["100", "@bob=50%", "@alice=40%"],
            mentioned_usernames=["@bob=50%", "@alice=40%"],
        )

        messenger.send_message.assert_called_once()
        svc.add_expense_selected_users.assert_called_once()
