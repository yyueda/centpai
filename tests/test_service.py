from datetime import datetime

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from pytest_mock import MockerFixture
from sqlalchemy.exc import IntegrityError
from app.core.errors import DomainError
from app.features.expenses.dto import BalanceDTO
from app.features.expenses.errors import ChatNotFound, ExpenseNotFoundError, ExpenseNotOwnedError, NotMember, ServerError, UserNotRegistered
from app.features.expenses.repo import ExpensesRepository
from app.features.expenses.service import ExpensesService


@pytest.fixture
def mock_repo(mocker: MockerFixture) -> Mock:
    repo = mocker.Mock(spec=ExpensesRepository)
    repo.db = Mock()
    repo.db.begin = AsyncMock()
    repo.db.commit = AsyncMock()
    repo.db.rollback = AsyncMock()
    return repo


@pytest.fixture
def service(mock_repo: Mock) -> ExpensesService:
    return ExpensesService(repo=mock_repo)


class TestMembership:

    async def test_add_member_success(
        self, service: ExpensesService, mock_repo: Mock, mocker: MockerFixture
    ) -> None:
        mock_repo.get_or_create_chat.return_value = mocker.Mock(id=10)
        mock_repo.get_or_create_user.return_value = mocker.Mock(id=1)

        await service.add_member(123, 456, username="junhong")

        mock_repo.db.begin.assert_called_once()
        mock_repo.db.commit.assert_called_once()
        mock_repo.add_member.assert_called_once_with(10, 1)
        mock_repo.create_balance.assert_called_once_with(10, 1)

    async def test_add_member_integrity_error_raises_server_error(
        self, service: ExpensesService, mock_repo: Mock
    ) -> None:
        mock_repo.add_member.side_effect = IntegrityError(None, None, Exception())

        with pytest.raises(ServerError):
            await service.add_member(123, 456)

        mock_repo.db.rollback.assert_called_once()
        mock_repo.db.commit.assert_not_called()

    async def test_remove_member_success(
        self, service: ExpensesService, mock_repo: Mock, mocker: MockerFixture
    ) -> None:
        mock_repo.get_user_by_tg_id.return_value = mocker.Mock(id=1)
        mock_repo.get_chat_by_tg_id.return_value = mocker.Mock(id=10)
        mock_repo.is_member.return_value = True

        await service.remove_member(10, 1)

        mock_repo.remove_member.assert_called_once_with(10, 1)
        mock_repo.db.commit.assert_called_once()


    @pytest.mark.parametrize("user, chat, is_member, expected_error", [
        (None, Mock(), True, UserNotRegistered),
        (Mock(), None, True, ChatNotFound),
        (Mock(), Mock(), False, NotMember),
    ])
    async def test_remove_member_validation_errors(
        self, service, mock_repo, user, chat, is_member, expected_error
    ):
        mock_repo.get_user_by_tg_id.return_value = user
        mock_repo.get_chat_by_tg_id.return_value = chat
        mock_repo.is_member.return_value = is_member

        with pytest.raises(expected_error):
            await service.remove_member(123, 456)
        
        mock_repo.db.rollback.assert_called_once()
        mock_repo.db.commit.assert_not_called()

    
    async def test_remove_member_integrity_error_raises_server_error(
        self, service: ExpensesService, mock_repo: Mock
    ) -> None:
        mock_repo.remove_member.side_effect = IntegrityError(None, None, Exception())

        with pytest.raises(ServerError):
            await service.remove_member(123, 456)

        mock_repo.db.rollback.assert_called_once()
        mock_repo.db.commit.assert_not_called()
    
    async def test_get_members_success(
        self, service: ExpensesService, mock_repo: Mock, mocker: MockerFixture
    ) -> None:
        member1 = mocker.Mock()
        member1.user.username = "alice"
        member2 = mocker.Mock()
        member2.user.username = "bob"

        mock_repo.get_chat_by_tg_id.return_value = mocker.Mock(id=1)
        mock_repo.list_members.return_value = [member1, member2]

        result = await service.get_members(1)

        mock_repo.list_members.assert_called_once_with(1)
        assert result == ["alice", "bob"]

    async def test_get_members_chat_not_found(
        self, service: ExpensesService, mock_repo: Mock
    ) -> None:
        mock_repo.get_chat_by_tg_id.return_value = None

        with pytest.raises(ChatNotFound):
            await service.get_members(999)

class TestExpenses:

    async def test_add_expense_success(
        self, service: ExpensesService, mock_repo: Mock, mocker: MockerFixture
    ) -> None:
        member1 = mocker.Mock(user_id=1)
        member2 = mocker.Mock(user_id=2)

        balance1 = mocker.Mock()
        balance1.user.username = "alice"
        balance1.balance = Decimal("5")
        balance2 = mocker.Mock()
        balance2.user.username = "bob"
        balance2.balance = Decimal("-5")

        mock_repo.get_user_by_tg_id.return_value = mocker.Mock(id=1)
        mock_repo.get_chat_by_tg_id.return_value = mocker.Mock(id=10)
        mock_repo.is_member.return_value = True
        mock_repo.list_members.return_value = [member1, member2]
        mock_repo.update_balances.return_value = [balance1, balance2]

        amount = Decimal("10.00")
        result = await service.add_expense(10, 1, amount, "lunch")

        mock_repo.db.begin.assert_called_once()
        mock_repo.create_expense.assert_called_once_with(10, 1, amount, "lunch")
        mock_repo.update_balances.assert_called_once()
        mock_repo.db.commit.assert_called_once()
        assert result == [
            BalanceDTO(username="alice", balance=Decimal("5")),
            BalanceDTO(username="bob", balance=Decimal("-5")),
        ]

    @pytest.mark.parametrize("user, chat, is_member, expected_error", [
        (None, Mock(), False, UserNotRegistered),
        (Mock(), None, True, ChatNotFound),
        (Mock(), Mock(), False, NotMember),
    ])
    async def test_add_expense_validation_errors(
        self, service: ExpensesService, mock_repo: Mock, user, chat, is_member, expected_error
    ) -> None:
        mock_repo.get_user_by_tg_id.return_value = user
        mock_repo.get_chat_by_tg_id.return_value = chat
        mock_repo.is_member.return_value = is_member

        with pytest.raises(expected_error):
            await service.add_expense(10, 1, Decimal("10.00"), "lunch")

        mock_repo.db.rollback.assert_called_once()
        mock_repo.db.commit.assert_not_called()

    async def test_add_expense_integrity_error_raises_server_error(
        self, service: ExpensesService, mock_repo: Mock, mocker: MockerFixture
    ) -> None:
        mock_repo.get_user_by_tg_id.return_value = mocker.Mock(id=1)
        mock_repo.get_chat_by_tg_id.return_value = mocker.Mock(id=10)
        mock_repo.is_member.return_value = True
        mock_repo.list_members.return_value = []
        mock_repo.create_expense.side_effect = IntegrityError(None, None, Exception())

        with pytest.raises(ServerError):
            await service.add_expense(111, 222, Decimal("10.00"), "lunch")

        mock_repo.db.rollback.assert_called_once()
        mock_repo.db.commit.assert_not_called()
    

    async def test_get_expenses_success(
        self, service: ExpensesService, mock_repo: Mock, mocker: MockerFixture
    ) -> None:
        split = mocker.Mock()
        split.user.username = "bob"
        split.amount = Decimal("5.00")
    
        expense = mocker.Mock()
        expense.id = 1
        expense.payer.username = "alice"
        expense.amount = Decimal("10.00")
        expense.description = "lunch"
        expense.created_at = datetime(2026, 1, 1)
        expense.splits = [split]

        mock_repo.get_chat_by_tg_id.return_value = mocker.Mock(id=1)
        mock_repo.list_expenses.return_value = [expense]

        result = await service.get_expenses(1)

        mock_repo.get_chat_by_tg_id.assert_called_once_with(1)
        mock_repo.list_expenses.assert_called_once_with(1, 10)

        assert len(result) == 1
        assert result[0].paid_by == "alice"
        assert result[0].amount == Decimal("10.00")
        assert result[0].participants is not None
        assert result[0].participants[0].username == "bob"
        assert result[0].participants[0].amount_owed == Decimal("5.00")
    
    async def test_get_expenses_chat_not_found(
        self, service: ExpensesService, mock_repo: Mock
    ) -> None:
        mock_repo.get_chat_by_tg_id.return_value = None

        with pytest.raises(ChatNotFound):
            await service.get_expenses(1)
    

    async def test_remove_expense_success(
        self, service: ExpensesService, mock_repo: Mock, mocker: MockerFixture
    ) -> None:
        user = mocker.Mock(id=1, username="alice")
        chat = mocker.Mock(id=10)                                                                                                                                                                       
        expense = mocker.Mock(id=99, payer_id=1)

        mock_repo.get_user_by_tg_id.return_value = user
        mock_repo.get_chat_by_tg_id.return_value = chat
        mock_repo.is_member.return_value = True
        mock_repo.get_expense.return_value = expense

        await service.remove_expense(10, 1, 99)

        mock_repo.get_expense.assert_called_once_with(10, 99)
        mock_repo.remove_expense.assert_called_once_with(expense)
        mock_repo.db.commit.assert_called_once()
        mock_repo.db.rollback.assert_not_called()


    @pytest.mark.parametrize("user, chat, is_member, expense, expected_error", [
        (None, Mock(), True, Mock(payer_id=1), UserNotRegistered),
        (Mock(id=1), None, True, Mock(payer_id=1), ChatNotFound),
        (Mock(id=1), Mock(), False, Mock(payer_id=1), NotMember),
        (Mock(id=1), Mock(), True, None, ExpenseNotFoundError),
        (Mock(id=1, username="alice"), Mock(), True, Mock(payer_id=99), ExpenseNotOwnedError),
    ])
    async def test_remove_expense_validation_errors(
        self, service, mock_repo, user, chat, is_member, expense, expected_error
    ) -> None:
        mock_repo.get_user_by_tg_id.return_value = user
        mock_repo.get_chat_by_tg_id.return_value = chat
        mock_repo.is_member.return_value = is_member
        mock_repo.get_expense.return_value = expense

        with pytest.raises(expected_error):
            await service.remove_expense(111, 222, expense_id=99)

        mock_repo.db.rollback.assert_called_once()
        mock_repo.db.commit.assert_not_called()

    async def test_remove_expense_integrity_error_raises_server_error(
        self, service: ExpensesService, mock_repo: Mock, mocker: MockerFixture
    ) -> None:
        mock_repo.get_user_by_tg_id.return_value = mocker.Mock(id=1, username="alice")
        mock_repo.get_chat_by_tg_id.return_value = mocker.Mock(id=10)
        mock_repo.is_member.return_value = True
        mock_repo.get_expense.return_value = mocker.Mock(payer_id=1)
        mock_repo.remove_expense.side_effect = IntegrityError(None, None, Exception())

        with pytest.raises(ServerError):
            await service.remove_expense(111, 222, expense_id=99)

        mock_repo.db.rollback.assert_called_once()
        mock_repo.db.commit.assert_not_called()


class TestBalances:

    async def test_get_balances_success(
        self, service: ExpensesService, mock_repo: Mock, mocker: MockerFixture
    ) -> None:
        user = mocker.Mock(id=1, username="alice")
        chat = mocker.Mock(id=10)                                                                                                                                                                       
        balance = mocker.Mock(user=user, balance=Decimal("10.00"))
    
        mock_repo.get_chat_by_tg_id.return_value = chat
        mock_repo.list_balances.return_value = [balance]

        result = await service.get_balances(1)

        mock_repo.list_balances.assert_called_once_with(10)
        assert result == [
            BalanceDTO(username="alice", balance=Decimal("10.00")),
        ]

    async def test_get_balances_chat_not_found(
        self, service: ExpensesService, mock_repo: Mock, mocker: MockerFixture
    ) -> None:
        mock_repo.get_chat_by_tg_id.return_value = None

        with pytest.raises(DomainError):
            await service.get_balances(1)
    

    async def test_simplified_debts_success(
        self, service: ExpensesService, mock_repo: Mock, mocker: MockerFixture
    ) -> None:
        balance1 = mocker.Mock()
        balance1.user.username = "alice"
        balance1.balance = Decimal("-20.00")

        balance2 = mocker.Mock()
        balance2.user.username = "bob"
        balance2.balance = Decimal("20.00")

        mock_repo.get_chat_by_tg_id.return_value = mocker.Mock(id=10)
        mock_repo.list_balances.return_value = [balance1, balance2]

        result = await service.get_simplified_debts(1)

        mock_repo.list_balances.assert_called_once_with(10)
        assert len(result) == 1
        assert result[0].from_user == "alice"
        assert result[0].to_user == "bob"
        assert result[0].amount == Decimal("20.00")

    
    async def test_simplified_debts_chat_not_found(
        self, service: ExpensesService, mock_repo: Mock, mocker: MockerFixture
    ) -> None:
        mock_repo.get_chat_by_tg_id.return_value = None

        with pytest.raises(DomainError):
            await service.get_simplified_debts(1)
        

class TestPayments:

    async def test_process_payment_success(
        self, service: ExpensesService, mock_repo: Mock, mocker: MockerFixture
    ) -> None:
        tg_chat_id, tg_user_id = 111, 222
        to_username = "bob"
        amount = Decimal("50.00")

        user_sender = mocker.Mock(id=1, username="alice")
        user_receiver = mocker.Mock(id=2, username="bob")
        chat = mocker.Mock(id=10)

        mock_repo.get_user_by_tg_id.return_value = user_sender
        mock_repo.get_user_by_username.return_value = user_receiver
        mock_repo.get_chat_by_tg_id.return_value = chat
        mock_repo.is_member.return_value = True
        mock_repo.get_pairwise_debt.return_value = Decimal("100.00")

        await service.process_payment(tg_chat_id, tg_user_id, to_username, amount)

        mock_repo.create_payment.assert_called_once_with(10, 1, 2, amount)
        mock_repo.update_balance.assert_called_once_with(10, 1, 2, amount)
        mock_repo.db.commit.assert_called_once()


class TestSplitCalculation:

    def test_calc_equal_split_rounding(self, service: ExpensesService) -> None:
        """
        Tests the math for an uneven split (e.g., $10 / 3 people).
        $10 / 3 = 3.3333... -> should be 3.33
        """
        amount = Decimal("10.00")
        payer_id = 1
        member_ids = [1, 2, 3]

        deltas = service._calc_equal_split_deltas(amount, payer_id, member_ids)

        # Non-payers owe 3.33
        # First member absorbs rounding diff
        assert deltas[2] == Decimal("-3.34")
        assert deltas[3] == Decimal("-3.33")
        # Payer gets: - 3.33 + 10 = 6.67
        assert deltas[1] == Decimal("6.67")

        # Sum has to equal to 0
        assert deltas[1] + deltas[2] + deltas[3] == Decimal("0.00")
    
    def test_calc_equal_split_zero_members(self, service: ExpensesService) -> None:
        """
        Tests if member_ids is an empty list.
        Payer will get full amount.
        """
        amount = Decimal("10.00")
        payer_id = 1
        member_ids = []

        deltas = service._calc_equal_split_deltas(amount, payer_id, member_ids)

        # Payer gets: 10
        assert deltas[1] == Decimal("10.00")
