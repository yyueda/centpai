import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from app.features.expenses.models import (
    utcnow,
    Base,
    Chat,
    User,
    ChatMember,
    Expense,
    ExpenseSplit,
    Payment,
    Balance,
)


class TestUtcnow:
    def test_returns_datetime(self):
        result = utcnow()
        assert isinstance(result, datetime)

    def test_returns_utc_timezone(self):
        result = utcnow()
        assert result.tzinfo == timezone.utc

    def test_is_recent(self):
        before = datetime.now(timezone.utc)
        result = utcnow()
        after = datetime.now(timezone.utc)
        assert before <= result <= after


class TestChatModel:
    def test_tablename(self):
        assert Chat.__tablename__ == "chats"

    def test_can_instantiate(self):
        chat = Chat(telegram_chat_id=12345)
        assert chat.telegram_chat_id == 12345

    def test_relationships_exist(self):
        assert hasattr(Chat, "members")
        assert hasattr(Chat, "expenses")
        assert hasattr(Chat, "payments")
        assert hasattr(Chat, "balances")

    def test_id_is_mapped(self):
        assert hasattr(Chat, "id")

    def test_telegram_chat_id_is_mapped(self):
        assert hasattr(Chat, "telegram_chat_id")


class TestUserModel:
    def test_tablename(self):
        assert User.__tablename__ == "users"

    def test_can_instantiate(self):
        user = User(
            telegram_user_id=999,
            username="alice",
            first_name="Alice",
            last_name="Smith",
        )
        assert user.telegram_user_id == 999
        assert user.username == "alice"
        assert user.first_name == "Alice"
        assert user.last_name == "Smith"

    def test_last_name_optional(self):
        user = User(telegram_user_id=1, username="bob", first_name="Bob")
        assert user.last_name is None

    def test_relationships_exist(self):
        assert hasattr(User, "chats")
        assert hasattr(User, "paid_expenses")
        assert hasattr(User, "owed_splits")
        assert hasattr(User, "sent_payments")
        assert hasattr(User, "received_payments")
        assert hasattr(User, "balances")


class TestChatMemberModel:
    def test_tablename(self):
        assert ChatMember.__tablename__ == "chat_members"

    def test_can_instantiate(self):
        member = ChatMember(chat_id=1, user_id=2)
        assert member.chat_id == 1
        assert member.user_id == 2

    def test_relationships_exist(self):
        assert hasattr(ChatMember, "chat")
        assert hasattr(ChatMember, "user")

    def test_table_args_has_unique_constraint(self):
        constraint_names = [
            c.name for c in ChatMember.__table_args__
            if hasattr(c, "name")
        ]
        assert "uq_chat_member" in constraint_names


class TestExpenseModel:
    def test_tablename(self):
        assert Expense.__tablename__ == "expenses"

    def test_can_instantiate(self):
        expense = Expense(
            chat_id=1,
            payer_id=2,
            amount=Decimal("50.00"),
            description="Dinner",
        )
        assert expense.chat_id == 1
        assert expense.payer_id == 2
        assert expense.amount == Decimal("50.00")
        assert expense.description == "Dinner"

    def test_relationships_exist(self):
        assert hasattr(Expense, "chat")
        assert hasattr(Expense, "payer")
        assert hasattr(Expense, "splits")


class TestExpenseSplitModel:
    def test_tablename(self):
        assert ExpenseSplit.__tablename__ == "expense_splits"

    def test_can_instantiate(self):
        split = ExpenseSplit(expense_id=1, user_id=2, amount=Decimal("25.00"))
        assert split.expense_id == 1
        assert split.user_id == 2
        assert split.amount == Decimal("25.00")

    def test_relationships_exist(self):
        assert hasattr(ExpenseSplit, "expense")
        assert hasattr(ExpenseSplit, "user")

    def test_table_args_has_unique_constraint(self):
        constraint_names = [
            c.name for c in ExpenseSplit.__table_args__
            if hasattr(c, "name")
        ]
        assert "uq_expense_split_user" in constraint_names

    def test_table_args_has_check_constraint(self):
        constraint_names = [
            c.name for c in ExpenseSplit.__table_args__
            if hasattr(c, "name")
        ]
        assert "ck_split_amount_non_negative" in constraint_names


class TestPaymentModel:
    def test_tablename(self):
        assert Payment.__tablename__ == "payments"

    def test_can_instantiate(self):
        payment = Payment(
            chat_id=1,
            from_user_id=2,
            to_user_id=3,
            amount=Decimal("20.00"),
        )
        assert payment.chat_id == 1
        assert payment.from_user_id == 2
        assert payment.to_user_id == 3
        assert payment.amount == Decimal("20.00")

    def test_relationships_exist(self):
        assert hasattr(Payment, "chat")
        assert hasattr(Payment, "from_user")
        assert hasattr(Payment, "to_user")

    def test_table_args_has_amount_check(self):
        constraint_names = [
            c.name for c in Payment.__table_args__
            if hasattr(c, "name")
        ]
        assert "ck_payment_amount_positive" in constraint_names

    def test_table_args_has_self_payment_check(self):
        constraint_names = [
            c.name for c in Payment.__table_args__
            if hasattr(c, "name")
        ]
        assert "ck_payment_not_to_self" in constraint_names


class TestBalanceModel:
    def test_tablename(self):
        assert Balance.__tablename__ == "balances"

    def test_can_instantiate(self):
        balance = Balance(chat_id=1, user_id=2, balance=Decimal("15.00"))
        assert balance.chat_id == 1
        assert balance.user_id == 2
        assert balance.balance == Decimal("15.00")

    def test_relationships_exist(self):
        assert hasattr(Balance, "chat")
        assert hasattr(Balance, "user")

    def test_table_args_has_unique_constraint(self):
        constraint_names = [
            c.name for c in Balance.__table_args__
            if hasattr(c, "name")
        ]
        assert "uq_chat_balance" in constraint_names

    def test_negative_balance(self):
        balance = Balance(chat_id=1, user_id=2, balance=Decimal("-10.00"))
        assert balance.balance == Decimal("-10.00")

    def test_zero_balance(self):
        balance = Balance(chat_id=1, user_id=2, balance=Decimal("0.00"))
        assert balance.balance == Decimal("0.00")


class TestBaseInheritance:
    def test_all_models_inherit_base(self):
        for model in [Chat, User, ChatMember, Expense, ExpenseSplit, Payment, Balance]:
            assert issubclass(model, Base)