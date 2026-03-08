import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.exc import IntegrityError

from app.features.expenses.service import ExpensesService
from app.features.expenses.errors import (
    ChatNotFound,
    NotMember,
    ServerError,
    UserNotRegistered,
    ExpenseNotFoundError,
    ExpenseNotOwnedError,
    NoDebtOwedError,
    PaymentExceedsDebtError,
)
from app.features.expenses.dto import BalanceDTO, ExpenseDTO, SimplifiedDebtDTO


def make_repo():
    repo = MagicMock()
    repo.db = MagicMock()
    repo.db.begin = AsyncMock()
    repo.db.commit = AsyncMock()
    repo.db.rollback = AsyncMock()
    repo.get_or_create_chat = AsyncMock()
    repo.get_or_create_user = AsyncMock()
    repo.get_chat_by_tg_id = AsyncMock()
    repo.get_user_by_tg_id = AsyncMock()
    repo.get_user_by_username = AsyncMock()
    repo.add_member = AsyncMock()
    repo.remove_member = AsyncMock()
    repo.is_member = AsyncMock()
    repo.list_members = AsyncMock()
    repo.create_balance = AsyncMock()
    repo.create_expense = AsyncMock()
    repo.update_balances = AsyncMock()
    repo.list_expenses = AsyncMock()
    repo.get_expense = AsyncMock()
    repo.remove_expense = AsyncMock()
    repo.list_balances = AsyncMock()
    repo.create_payment = AsyncMock()
    repo.update_balance = AsyncMock()
    repo.get_pairwise_debt = AsyncMock()
    return repo


def make_chat(id=1):
    chat = MagicMock()
    chat.id = id
    return chat


def make_user(id=1, username="alice"):
    user = MagicMock()
    user.id = id
    user.username = username
    return user


def make_member(user_id=1, username="alice"):
    member = MagicMock()
    member.user_id = user_id
    member.user = MagicMock()
    member.user.username = username
    return member


def make_balance_obj(user_id=1, username="alice", balance=Decimal("0.00")):
    bal = MagicMock()
    bal.user_id = user_id
    bal.user = MagicMock()
    bal.user.username = username
    bal.balance = balance
    return bal


def make_expense_obj(
    id=1, payer_username="alice", amount=Decimal("50.00"), splits=None
):
    expense = MagicMock()
    expense.id = id
    expense.payer = MagicMock()
    expense.payer.username = payer_username
    expense.payer_id = 1
    expense.amount = amount
    expense.description = "Dinner"
    expense.created_at = MagicMock()
    expense.splits = splits or []
    return expense


# ------------------------------------------------------------------
# ADD MEMBER
# ------------------------------------------------------------------


class TestAddMember:
    @pytest.mark.asyncio
    async def test_successful_add_member(self):
        repo = make_repo()
        chat = make_chat()
        user = make_user()
        repo.get_or_create_chat.return_value = chat
        repo.get_or_create_user.return_value = user
        svc = ExpensesService(repo)
        await svc.add_member(100, 42, username="alice")
        repo.add_member.assert_called_once_with(chat.id, user.id)
        repo.create_balance.assert_called_once_with(chat.id, user.id)
        repo.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_integrity_error_raises_server_error(self):
        repo = make_repo()
        repo.get_or_create_chat.side_effect = IntegrityError(None, None, None)
        svc = ExpensesService(repo)
        with pytest.raises(ServerError):
            await svc.add_member(100, 42)
        repo.db.rollback.assert_called_once()


# ------------------------------------------------------------------
# REMOVE MEMBER
# ------------------------------------------------------------------


class TestRemoveMember:
    @pytest.mark.asyncio
    async def test_successful_remove(self):
        repo = make_repo()
        chat = make_chat()
        user = make_user()
        repo.get_user_by_tg_id.return_value = user
        repo.get_chat_by_tg_id.return_value = chat
        repo.is_member.return_value = True
        svc = ExpensesService(repo)
        await svc.remove_member(100, 42)
        repo.remove_member.assert_called_once_with(chat.id, 42)
        repo.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_user_not_registered(self):
        repo = make_repo()
        repo.get_user_by_tg_id.return_value = None
        svc = ExpensesService(repo)
        with pytest.raises(UserNotRegistered):
            await svc.remove_member(100, 42)
        repo.db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_chat_not_found(self):
        repo = make_repo()
        repo.get_user_by_tg_id.return_value = make_user()
        repo.get_chat_by_tg_id.return_value = None
        svc = ExpensesService(repo)
        with pytest.raises(ChatNotFound):
            await svc.remove_member(100, 42)
        repo.db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_not_member(self):
        repo = make_repo()
        repo.get_user_by_tg_id.return_value = make_user()
        repo.get_chat_by_tg_id.return_value = make_chat()
        repo.is_member.return_value = False
        svc = ExpensesService(repo)
        with pytest.raises(NotMember):
            await svc.remove_member(100, 42)
        repo.db.rollback.assert_called_once()


# ------------------------------------------------------------------
# GET MEMBERS
# ------------------------------------------------------------------


class TestGetMembers:
    @pytest.mark.asyncio
    async def test_returns_usernames(self):
        repo = make_repo()
        repo.get_chat_by_tg_id.return_value = make_chat()
        repo.list_members.return_value = [
            make_member(username="alice"),
            make_member(username="bob"),
        ]
        svc = ExpensesService(repo)
        result = await svc.get_members(100)
        assert result == ["alice", "bob"]

    @pytest.mark.asyncio
    async def test_raises_chat_not_found(self):
        repo = make_repo()
        repo.get_chat_by_tg_id.return_value = None
        svc = ExpensesService(repo)
        with pytest.raises(ChatNotFound):
            await svc.get_members(100)

    @pytest.mark.asyncio
    async def test_falls_back_to_user_id_when_no_username(self):
        repo = make_repo()
        repo.get_chat_by_tg_id.return_value = make_chat()
        member = MagicMock()
        member.user_id = 99
        member.user.username = None
        member.user.id = 99
        repo.list_members.return_value = [member]
        svc = ExpensesService(repo)
        result = await svc.get_members(100)
        assert result == ["99"]


# ------------------------------------------------------------------
# ADD EXPENSE
# ------------------------------------------------------------------


class TestAddExpense:
    @pytest.mark.asyncio
    async def test_successful_add_expense(self):
        repo = make_repo()
        user = make_user()
        chat = make_chat()
        bal = make_balance_obj(username="alice", balance=Decimal("40.00"))
        repo.get_user_by_tg_id.return_value = user
        repo.get_chat_by_tg_id.return_value = chat
        repo.is_member.return_value = True
        repo.list_members.return_value = [make_member(user_id=1)]
        repo.update_balances.return_value = [bal]
        svc = ExpensesService(repo)
        result = await svc.add_expense(100, 42, Decimal("50.00"), "Dinner")
        assert isinstance(result, list)
        assert result[0].username == "alice"
        repo.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_user_not_registered(self):
        repo = make_repo()
        repo.get_user_by_tg_id.return_value = None
        svc = ExpensesService(repo)
        with pytest.raises(UserNotRegistered):
            await svc.add_expense(100, 42, Decimal("10.00"), "x")
        repo.db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_chat_not_found(self):
        repo = make_repo()
        repo.get_user_by_tg_id.return_value = make_user()
        repo.get_chat_by_tg_id.return_value = None
        svc = ExpensesService(repo)
        with pytest.raises(ChatNotFound):
            await svc.add_expense(100, 42, Decimal("10.00"), "x")
        repo.db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_not_member(self):
        repo = make_repo()
        repo.get_user_by_tg_id.return_value = make_user()
        repo.get_chat_by_tg_id.return_value = make_chat()
        repo.is_member.return_value = False
        svc = ExpensesService(repo)
        with pytest.raises(NotMember):
            await svc.add_expense(100, 42, Decimal("10.00"), "x")
        repo.db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_integrity_error_raises_server_error(self):
        repo = make_repo()
        repo.get_user_by_tg_id.side_effect = IntegrityError(None, None, None)
        svc = ExpensesService(repo)
        with pytest.raises(ServerError):
            await svc.add_expense(100, 42, Decimal("10.00"), "x")
        repo.db.rollback.assert_called_once()


# ------------------------------------------------------------------
# GET EXPENSES
# ------------------------------------------------------------------


class TestGetExpenses:
    @pytest.mark.asyncio
    async def test_returns_expense_dtos(self):
        repo = make_repo()
        repo.get_chat_by_tg_id.return_value = make_chat()
        repo.list_expenses.return_value = [make_expense_obj()]
        svc = ExpensesService(repo)
        result = await svc.get_expenses(100)
        assert len(result) == 1
        assert isinstance(result[0], ExpenseDTO)
        assert result[0].paid_by == "alice"

    @pytest.mark.asyncio
    async def test_raises_chat_not_found(self):
        repo = make_repo()
        repo.get_chat_by_tg_id.return_value = None
        svc = ExpensesService(repo)
        with pytest.raises(ChatNotFound):
            await svc.get_expenses(100)

    @pytest.mark.asyncio
    async def test_returns_empty_list(self):
        repo = make_repo()
        repo.get_chat_by_tg_id.return_value = make_chat()
        repo.list_expenses.return_value = []
        svc = ExpensesService(repo)
        result = await svc.get_expenses(100)
        assert result == []


# ------------------------------------------------------------------
# REMOVE EXPENSE
# ------------------------------------------------------------------


class TestRemoveExpense:
    @pytest.mark.asyncio
    async def test_successful_remove(self):
        repo = make_repo()
        user = make_user(id=1)
        expense = make_expense_obj()
        expense.payer_id = 1
        repo.get_user_by_tg_id.return_value = user
        repo.get_chat_by_tg_id.return_value = make_chat()
        repo.is_member.return_value = True
        repo.get_expense.return_value = expense
        svc = ExpensesService(repo)
        await svc.remove_expense(100, 42, expense_id=1)
        repo.remove_expense.assert_called_once_with(expense)
        repo.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_expense_not_found(self):
        repo = make_repo()
        repo.get_user_by_tg_id.return_value = make_user()
        repo.get_chat_by_tg_id.return_value = make_chat()
        repo.is_member.return_value = True
        repo.get_expense.return_value = None
        svc = ExpensesService(repo)
        with pytest.raises(ExpenseNotFoundError):
            await svc.remove_expense(100, 42, expense_id=99)
        repo.db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_expense_not_owned(self):
        repo = make_repo()
        user = make_user(id=1)
        expense = make_expense_obj()
        expense.payer_id = 999  # different user owns it
        repo.get_user_by_tg_id.return_value = user
        repo.get_chat_by_tg_id.return_value = make_chat()
        repo.is_member.return_value = True
        repo.get_expense.return_value = expense
        svc = ExpensesService(repo)
        with pytest.raises(ExpenseNotOwnedError):
            await svc.remove_expense(100, 42, expense_id=1)
        repo.db.rollback.assert_called_once()


# ------------------------------------------------------------------
# GET BALANCES
# ------------------------------------------------------------------


class TestGetBalances:
    @pytest.mark.asyncio
    async def test_returns_balance_dtos(self):
        repo = make_repo()
        repo.get_chat_by_tg_id.return_value = make_chat()
        repo.list_balances.return_value = [
            make_balance_obj(username="alice", balance=Decimal("10.00"))
        ]
        svc = ExpensesService(repo)
        result = await svc.get_balances(100)
        assert len(result) == 1
        assert isinstance(result[0], BalanceDTO)
        assert result[0].username == "alice"

    @pytest.mark.asyncio
    async def test_raises_chat_not_found(self):
        repo = make_repo()
        repo.get_chat_by_tg_id.return_value = None
        svc = ExpensesService(repo)
        with pytest.raises(ChatNotFound):
            await svc.get_balances(100)


# ------------------------------------------------------------------
# GET SIMPLIFIED DEBTS
# ------------------------------------------------------------------


class TestGetSimplifiedDebts:
    @pytest.mark.asyncio
    async def test_returns_simplified_debt_dtos(self):
        repo = make_repo()
        repo.get_chat_by_tg_id.return_value = make_chat()
        repo.list_balances.return_value = [
            make_balance_obj(username="alice", balance=Decimal("-10.00")),
            make_balance_obj(username="bob", balance=Decimal("10.00")),
        ]
        svc = ExpensesService(repo)
        result = await svc.get_simplified_debts(100)
        assert len(result) >= 1
        assert isinstance(result[0], SimplifiedDebtDTO)

    @pytest.mark.asyncio
    async def test_raises_chat_not_found(self):
        repo = make_repo()
        repo.get_chat_by_tg_id.return_value = None
        svc = ExpensesService(repo)
        with pytest.raises(ChatNotFound):
            await svc.get_simplified_debts(100)

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_settled(self):
        repo = make_repo()
        repo.get_chat_by_tg_id.return_value = make_chat()
        repo.list_balances.return_value = [
            make_balance_obj(username="alice", balance=Decimal("0.00"))
        ]
        svc = ExpensesService(repo)
        result = await svc.get_simplified_debts(100)
        assert result == []


# ------------------------------------------------------------------
# PROCESS PAYMENT
# ------------------------------------------------------------------


class TestProcessPayment:
    @pytest.mark.asyncio
    async def test_successful_payment(self):
        repo = make_repo()
        user = make_user(id=1, username="alice")
        to_user = make_user(id=2, username="bob")
        chat = make_chat()
        repo.get_user_by_tg_id.return_value = user
        repo.get_user_by_username.return_value = to_user
        repo.get_chat_by_tg_id.return_value = chat
        repo.is_member.return_value = True
        repo.get_pairwise_debt.return_value = Decimal("20.00")
        svc = ExpensesService(repo)
        await svc.process_payment(100, 42, "bob", Decimal("10.00"))
        repo.create_payment.assert_called_once()
        repo.update_balance.assert_called_once()
        repo.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_user_not_registered(self):
        repo = make_repo()
        repo.get_user_by_tg_id.return_value = None
        svc = ExpensesService(repo)
        with pytest.raises(UserNotRegistered):
            await svc.process_payment(100, 42, "bob", Decimal("10.00"))

    @pytest.mark.asyncio
    async def test_raises_to_user_not_registered(self):
        repo = make_repo()
        repo.get_user_by_tg_id.return_value = make_user()
        repo.get_user_by_username.return_value = None
        svc = ExpensesService(repo)
        with pytest.raises(UserNotRegistered):
            await svc.process_payment(100, 42, "ghost", Decimal("10.00"))

    @pytest.mark.asyncio
    async def test_raises_no_debt_owed(self):
        repo = make_repo()
        repo.get_user_by_tg_id.return_value = make_user(id=1)
        repo.get_user_by_username.return_value = make_user(id=2)
        repo.get_chat_by_tg_id.return_value = make_chat()
        repo.is_member.return_value = True
        repo.get_pairwise_debt.return_value = Decimal("0")
        svc = ExpensesService(repo)
        with pytest.raises(NoDebtOwedError):
            await svc.process_payment(100, 42, "bob", Decimal("10.00"))

    @pytest.mark.asyncio
    async def test_raises_payment_exceeds_debt(self):
        repo = make_repo()
        repo.get_user_by_tg_id.return_value = make_user(id=1)
        repo.get_user_by_username.return_value = make_user(id=2)
        repo.get_chat_by_tg_id.return_value = make_chat()
        repo.is_member.return_value = True
        repo.get_pairwise_debt.return_value = Decimal("5.00")
        svc = ExpensesService(repo)
        with pytest.raises(PaymentExceedsDebtError):
            await svc.process_payment(100, 42, "bob", Decimal("10.00"))

    @pytest.mark.asyncio
    async def test_raises_not_member_for_payer(self):
        repo = make_repo()
        repo.get_user_by_tg_id.return_value = make_user(id=1)
        repo.get_user_by_username.return_value = make_user(id=2)
        repo.get_chat_by_tg_id.return_value = make_chat()
        repo.is_member.side_effect = [False]
        svc = ExpensesService(repo)
        with pytest.raises(NotMember):
            await svc.process_payment(100, 42, "bob", Decimal("5.00"))


# ------------------------------------------------------------------
# CALC EQUAL SPLIT DELTAS (static helper)
# ------------------------------------------------------------------


class TestCalcEqualSplitDeltas:
    def test_two_members_equal_split(self):
        result = ExpensesService._calc_equal_split_deltas(
            Decimal("10.00"), payer_id=1, member_ids=[1, 2]
        )
        assert result[1] == Decimal("5.00")  # payer gains amount - split
        assert result[2] == Decimal("-5.00")  # non-payer owes split

    def test_three_members_equal_split(self):
        result = ExpensesService._calc_equal_split_deltas(
            Decimal("30.00"), payer_id=1, member_ids=[1, 2, 3]
        )
        assert result[2] == Decimal("-10.00")
        assert result[3] == Decimal("-10.00")
        assert result[1] == Decimal("20.00")

    def test_payer_gets_positive_delta(self):
        result = ExpensesService._calc_equal_split_deltas(
            Decimal("50.00"), payer_id=5, member_ids=[5, 6]
        )
        assert result[5] > Decimal("0")

    def test_non_payers_get_negative_delta(self):
        result = ExpensesService._calc_equal_split_deltas(
            Decimal("50.00"), payer_id=1, member_ids=[1, 2, 3]
        )
        assert result[2] < Decimal("0")
        assert result[3] < Decimal("0")

    def test_single_member_payer(self):
        result = ExpensesService._calc_equal_split_deltas(
            Decimal("20.00"), payer_id=1, member_ids=[1]
        )
        # payer pays for themselves: amount - split = 20 - 20 = 0
        assert result[1] == Decimal("0.00")
