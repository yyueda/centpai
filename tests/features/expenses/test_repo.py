import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch, call
from sqlalchemy.exc import IntegrityError

from app.features.expenses.repo import ExpensesRepository
from app.features.expenses.models import (
    Balance,
    Chat,
    ChatMember,
    Expense,
    ExpenseSplit,
    Payment,
    User,
)


def make_db():
    db = MagicMock()
    db.scalar = AsyncMock()
    db.scalars = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.delete = AsyncMock()
    db.add = MagicMock()
    db.add_all = MagicMock()
    return db


def make_repo(db=None):
    return ExpensesRepository(db or make_db())


def make_chat(id=1, tg_id=100):
    chat = MagicMock(spec=Chat)
    chat.id = id
    chat.telegram_chat_id = tg_id
    return chat


def make_user(id=1, tg_id=42, username="alice"):
    user = MagicMock(spec=User)
    user.id = id
    user.telegram_user_id = tg_id
    user.username = username
    return user


def make_balance(user_id=1, chat_id=1, balance=Decimal("0.00")):
    bal = MagicMock(spec=Balance)
    bal.user_id = user_id
    bal.chat_id = chat_id
    bal.balance = balance
    return bal


def make_scalars_result(items):
    result = MagicMock()
    result.all = MagicMock(return_value=items)
    return result


# ------------------------------------------------------------------
# CHATS
# ------------------------------------------------------------------


class TestGetChatByTgId:
    @pytest.mark.asyncio
    async def test_returns_chat_when_found(self):
        db = make_db()
        chat = make_chat()
        db.scalar.return_value = chat
        repo = make_repo(db)
        result = await repo.get_chat_by_tg_id(100)
        assert result == chat

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        db = make_db()
        db.scalar.return_value = None
        repo = make_repo(db)
        result = await repo.get_chat_by_tg_id(999)
        assert result is None


class TestGetOrCreateChat:
    @pytest.mark.asyncio
    async def test_returns_existing_chat(self):
        db = make_db()
        chat = make_chat()
        db.scalar.return_value = chat
        repo = make_repo(db)
        result = await repo.get_or_create_chat(100)
        assert result == chat
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_new_chat_when_not_found(self):
        db = make_db()
        db.scalar.return_value = None
        repo = make_repo(db)
        result = await repo.get_or_create_chat(100)
        db.add.assert_called_once()
        db.flush.assert_called_once()
        assert result.telegram_chat_id == 100

    @pytest.mark.asyncio
    async def test_handles_integrity_error_race_condition(self):
        db = make_db()
        chat = make_chat()
        db.scalar.side_effect = [None, chat]
        db.flush.side_effect = IntegrityError(None, None, None)
        repo = make_repo(db)
        result = await repo.get_or_create_chat(100)
        assert result == chat

    @pytest.mark.asyncio
    async def test_raises_if_integrity_error_and_still_no_chat(self):
        db = make_db()
        db.scalar.return_value = None
        db.flush.side_effect = IntegrityError(None, None, None)
        repo = make_repo(db)
        with pytest.raises(IntegrityError):
            await repo.get_or_create_chat(100)


# ------------------------------------------------------------------
# USERS
# ------------------------------------------------------------------


class TestGetUserByTgId:
    @pytest.mark.asyncio
    async def test_returns_user_when_found(self):
        db = make_db()
        user = make_user()
        db.scalar.return_value = user
        repo = make_repo(db)
        result = await repo.get_user_by_tg_id(42)
        assert result == user

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        db = make_db()
        db.scalar.return_value = None
        repo = make_repo(db)
        result = await repo.get_user_by_tg_id(999)
        assert result is None


class TestGetOrCreateUser:
    @pytest.mark.asyncio
    async def test_returns_existing_user(self):
        db = make_db()
        user = make_user()
        db.scalar.return_value = user
        repo = make_repo(db)
        result = await repo.get_or_create_user(42, username="alice")
        assert result == user
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_new_user(self):
        db = make_db()
        db.scalar.return_value = None
        repo = make_repo(db)
        result = await repo.get_or_create_user(
            42, username="alice", first_name="Alice", last_name="Smith"
        )
        db.add.assert_called_once()
        db.flush.assert_called_once()
        assert result.username == "alice"

    @pytest.mark.asyncio
    async def test_handles_integrity_error_race_condition(self):
        db = make_db()
        user = make_user()
        db.scalar.side_effect = [None, user]
        db.flush.side_effect = IntegrityError(None, None, None)
        repo = make_repo(db)
        result = await repo.get_or_create_user(42)
        assert result == user

    @pytest.mark.asyncio
    async def test_raises_if_integrity_error_and_still_no_user(self):
        db = make_db()
        db.scalar.return_value = None
        db.flush.side_effect = IntegrityError(None, None, None)
        repo = make_repo(db)
        with pytest.raises(IntegrityError):
            await repo.get_or_create_user(42)


class TestGetUserByUsername:
    @pytest.mark.asyncio
    async def test_returns_user(self):
        db = make_db()
        user = make_user()
        db.scalar.return_value = user
        repo = make_repo(db)
        result = await repo.get_user_by_username("alice")
        assert result == user

    @pytest.mark.asyncio
    async def test_returns_none(self):
        db = make_db()
        db.scalar.return_value = None
        repo = make_repo(db)
        result = await repo.get_user_by_username("nobody")
        assert result is None


# ------------------------------------------------------------------
# MEMBERS
# ------------------------------------------------------------------


class TestAddMember:
    @pytest.mark.asyncio
    async def test_executes_insert(self):
        db = make_db()
        repo = make_repo(db)
        await repo.add_member(chat_id=1, user_id=2)
        db.execute.assert_called_once()


class TestRemoveMember:
    @pytest.mark.asyncio
    async def test_returns_false_if_user_not_found(self):
        db = make_db()
        db.scalar.return_value = None
        repo = make_repo(db)
        result = await repo.remove_member(chat_id=1, tg_user_id=999)
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_if_not_a_member(self):
        db = make_db()
        user = make_user()
        db.scalar.side_effect = [user, None]
        repo = make_repo(db)
        result = await repo.remove_member(chat_id=1, tg_user_id=42)
        assert result is False

    @pytest.mark.asyncio
    async def test_deletes_and_returns_true(self):
        db = make_db()
        user = make_user()
        member = MagicMock(spec=ChatMember)
        db.scalar.side_effect = [user, member]
        repo = make_repo(db)
        result = await repo.remove_member(chat_id=1, tg_user_id=42)
        db.delete.assert_called_once_with(member)
        db.flush.assert_called_once()
        assert result is True


class TestListMembers:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        db = make_db()
        members = [MagicMock(spec=ChatMember), MagicMock(spec=ChatMember)]
        db.scalars.return_value = make_scalars_result(members)
        repo = make_repo(db)
        result = await repo.list_members(chat_id=1)
        assert result == members

    @pytest.mark.asyncio
    async def test_returns_empty_list(self):
        db = make_db()
        db.scalars.return_value = make_scalars_result([])
        repo = make_repo(db)
        result = await repo.list_members(chat_id=1)
        assert result == []


class TestIsMember:
    @pytest.mark.asyncio
    async def test_returns_true_when_member(self):
        db = make_db()
        db.scalar.return_value = 1  # some ID
        repo = make_repo(db)
        result = await repo.is_member(chat_id=1, user_id=2)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_not_member(self):
        db = make_db()
        db.scalar.return_value = None
        repo = make_repo(db)
        result = await repo.is_member(chat_id=1, user_id=2)
        assert result is False


# ------------------------------------------------------------------
# EXPENSES
# ------------------------------------------------------------------


class TestCreateExpense:
    @pytest.mark.asyncio
    async def test_adds_and_flushes(self):
        db = make_db()
        repo = make_repo(db)
        await repo.create_expense(
            chat_id=1, user_id=2, amount=Decimal("50.00"), description="Dinner"
        )
        db.add.assert_called_once()
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_expense_has_correct_fields(self):
        db = make_db()
        repo = make_repo(db)
        await repo.create_expense(
            chat_id=5, user_id=7, amount=Decimal("30.00"), description="Lunch"
        )
        added = db.add.call_args[0][0]
        assert added.chat_id == 5
        assert added.payer_id == 7
        assert added.amount == Decimal("30.00")
        assert added.description == "Lunch"


class TestAddSplits:
    @pytest.mark.asyncio
    async def test_adds_all_and_flushes(self):
        db = make_db()
        repo = make_repo(db)
        splits = [MagicMock(spec=ExpenseSplit), MagicMock(spec=ExpenseSplit)]
        await repo.add_splits(splits)
        db.add_all.assert_called_once_with(splits)
        db.flush.assert_called_once()


class TestListExpenses:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        db = make_db()
        expenses = [MagicMock(spec=Expense)]
        db.scalars.return_value = make_scalars_result(expenses)
        repo = make_repo(db)
        result = await repo.list_expenses(chat_id=1)
        assert result == expenses

    @pytest.mark.asyncio
    async def test_returns_empty_list(self):
        db = make_db()
        db.scalars.return_value = make_scalars_result([])
        repo = make_repo(db)
        result = await repo.list_expenses(chat_id=1)
        assert result == []


class TestGetExpense:
    @pytest.mark.asyncio
    async def test_returns_expense(self):
        db = make_db()
        expense = MagicMock(spec=Expense)
        db.scalar.return_value = expense
        repo = make_repo(db)
        result = await repo.get_expense(chat_id=1, expense_id=5)
        assert result == expense

    @pytest.mark.asyncio
    async def test_returns_none(self):
        db = make_db()
        db.scalar.return_value = None
        repo = make_repo(db)
        result = await repo.get_expense(chat_id=1, expense_id=999)
        assert result is None


class TestRemoveExpense:
    @pytest.mark.asyncio
    async def test_deletes_and_flushes(self):
        db = make_db()
        expense = MagicMock(spec=Expense)
        repo = make_repo(db)
        await repo.remove_expense(expense)
        db.delete.assert_called_once_with(expense)
        db.flush.assert_called_once()


# ------------------------------------------------------------------
# PAYMENTS
# ------------------------------------------------------------------


class TestCreatePayment:
    @pytest.mark.asyncio
    async def test_adds_and_flushes(self):
        db = make_db()
        repo = make_repo(db)
        await repo.create_payment(
            chat_id=1, from_user_id=2, to_user_id=3, amount=Decimal("20.00")
        )
        db.add.assert_called_once()
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_payment_has_correct_fields(self):
        db = make_db()
        repo = make_repo(db)
        await repo.create_payment(
            chat_id=1, from_user_id=2, to_user_id=3, amount=Decimal("20.00")
        )
        added = db.add.call_args[0][0]
        assert added.chat_id == 1
        assert added.from_user_id == 2
        assert added.to_user_id == 3
        assert added.amount == Decimal("20.00")


class TestListPayments:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        db = make_db()
        payments = [MagicMock(spec=Payment)]
        db.scalars.return_value = make_scalars_result(payments)
        repo = make_repo(db)
        result = await repo.list_payments(chat_id=1)
        assert result == payments


# ------------------------------------------------------------------
# BALANCES
# ------------------------------------------------------------------


class TestGetUserBalance:
    @pytest.mark.asyncio
    async def test_returns_balance(self):
        db = make_db()
        bal = make_balance()
        db.scalar.return_value = bal
        repo = make_repo(db)
        result = await repo.get_user_balance(chat_id=1, user_id=2)
        assert result == bal

    @pytest.mark.asyncio
    async def test_returns_none(self):
        db = make_db()
        db.scalar.return_value = None
        repo = make_repo(db)
        result = await repo.get_user_balance(chat_id=1, user_id=999)
        assert result is None


class TestCreateBalance:
    @pytest.mark.asyncio
    async def test_skips_if_balance_exists(self):
        db = make_db()
        db.scalar.return_value = make_balance()
        repo = make_repo(db)
        await repo.create_balance(chat_id=1, user_id=2)
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_balance_with_zero(self):
        db = make_db()
        db.scalar.return_value = None
        repo = make_repo(db)
        await repo.create_balance(chat_id=1, user_id=2)
        db.add.assert_called_once()
        added = db.add.call_args[0][0]
        assert added.balance == Decimal("0.00")
        assert added.chat_id == 1
        assert added.user_id == 2


class TestListBalances:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        db = make_db()
        balances = [make_balance(user_id=1), make_balance(user_id=2)]
        db.scalars.return_value = make_scalars_result(balances)
        repo = make_repo(db)
        result = await repo.list_balances(chat_id=1)
        assert result == balances


class TestUpdateBalances:
    @pytest.mark.asyncio
    async def test_applies_deltas_and_flushes(self):
        db = make_db()
        bal1 = make_balance(user_id=1, balance=Decimal("0.00"))
        bal2 = make_balance(user_id=2, balance=Decimal("0.00"))
        db.scalars.return_value = make_scalars_result([bal1, bal2])
        repo = make_repo(db)

        deltas = {1: Decimal("10.00"), 2: Decimal("-10.00")}
        await repo.update_balances(chat_id=1, deltas=deltas)

        assert bal1.balance == Decimal("10.00")
        assert bal2.balance == Decimal("-10.00")
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_updated_balances(self):
        db = make_db()
        bal = make_balance(user_id=1, balance=Decimal("0.00"))
        db.scalars.return_value = make_scalars_result([bal])
        repo = make_repo(db)
        result = await repo.update_balances(chat_id=1, deltas={1: Decimal("5.00")})
        assert isinstance(result, list)
        assert len(result) == 1


class TestUpdateBalance:
    @pytest.mark.asyncio
    async def test_adjusts_both_balances(self):
        db = make_db()
        from_bal = make_balance(user_id=1, balance=Decimal("0.00"))
        to_bal = make_balance(user_id=2, balance=Decimal("0.00"))
        db.scalar.side_effect = [from_bal, to_bal]
        repo = make_repo(db)

        await repo.update_balance(
            chat_id=1, from_user_id=1, to_user_id=2, amount=Decimal("15.00")
        )

        assert from_bal.balance == Decimal("15.00")
        assert to_bal.balance == Decimal("-15.00")
        db.flush.assert_called_once()


class TestGetPairwiseDebt:
    @pytest.mark.asyncio
    async def test_returns_debt_minus_paid(self):
        db = make_db()
        db.scalar.side_effect = [Decimal("30.00"), Decimal("10.00")]
        repo = make_repo(db)
        result = await repo.get_pairwise_debt(chat_id=1, from_user_id=1, to_user_id=2)
        assert result == Decimal("20.00")

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_owed_and_no_paid(self):
        db = make_db()
        db.scalar.side_effect = [None, None]
        repo = make_repo(db)
        result = await repo.get_pairwise_debt(chat_id=1, from_user_id=1, to_user_id=2)
        assert result == Decimal("0")

    @pytest.mark.asyncio
    async def test_returns_full_owed_when_nothing_paid(self):
        db = make_db()
        db.scalar.side_effect = [Decimal("50.00"), None]
        repo = make_repo(db)
        result = await repo.get_pairwise_debt(chat_id=1, from_user_id=1, to_user_id=2)
        assert result == Decimal("50.00")
