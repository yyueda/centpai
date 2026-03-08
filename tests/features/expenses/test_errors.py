import pytest
from decimal import Decimal
from app.features.expenses.errors import (
    NotMember,
    UserNotRegistered,
    ChatNotFound,
    ServerError,
    ExpenseNotFoundError,
    ExpenseNotOwnedError,
    NoDebtOwedError,
    PaymentExceedsDebtError,
)


class TestNotMember:
    def test_default_message(self):
        err = NotMember()
        assert "You" in err.message
        assert "are not a member" in err.message
        assert err.code == "not_member"

    def test_custom_username(self):
        err = NotMember(username="alice")
        assert "alice" in err.message
        assert "is not a member" in err.message
        assert err.code == "not_member"

    def test_default_uses_are(self):
        err = NotMember()
        assert "are" in err.message

    def test_custom_username_uses_is(self):
        err = NotMember(username="bob")
        assert "is" in err.message

    def test_is_exception(self):
        with pytest.raises(NotMember):
            raise NotMember()


class TestUserNotRegistered:
    def test_default_message(self):
        err = UserNotRegistered()
        assert "not registered" in err.message
        assert err.code == "user_not_registered"

    def test_custom_message(self):
        err = UserNotRegistered(message="Custom error")
        assert "Custom error" in err.message

    def test_is_exception(self):
        with pytest.raises(UserNotRegistered):
            raise UserNotRegistered()


class TestChatNotFound:
    def test_message(self):
        err = ChatNotFound()
        assert "Chat not found" in err.message
        assert err.code == "chat_not_found"

    def test_is_exception(self):
        with pytest.raises(ChatNotFound):
            raise ChatNotFound()


class TestServerError:
    def test_message(self):
        err = ServerError()
        assert "Error processing request" in err.message
        assert err.code == "server_error"

    def test_is_exception(self):
        with pytest.raises(ServerError):
            raise ServerError()


class TestExpenseNotFoundError:
    def test_message_contains_id(self):
        err = ExpenseNotFoundError(42)
        assert "42" in err.message

    def test_is_exception(self):
        with pytest.raises(ExpenseNotFoundError):
            raise ExpenseNotFoundError(1)


class TestExpenseNotOwnedError:
    def test_message_contains_id_and_username(self):
        err = ExpenseNotOwnedError(7, "alice")
        assert "7" in err.message
        assert "alice" in err.message

    def test_is_exception(self):
        with pytest.raises(ExpenseNotOwnedError):
            raise ExpenseNotOwnedError(1, "bob")


class TestNoDebtOwedError:
    def test_message_contains_username(self):
        err = NoDebtOwedError("bob")
        assert "bob" in err.message

    def test_is_exception(self):
        with pytest.raises(NoDebtOwedError):
            raise NoDebtOwedError("alice")


class TestPaymentExceedsDebtError:
    def test_message_contains_values(self):
        err = PaymentExceedsDebtError(Decimal("10.00"), Decimal("20.00"), "alice")
        assert "10" in err.message
        assert "20" in err.message
        assert "alice" in err.message

    def test_is_exception(self):
        with pytest.raises(PaymentExceedsDebtError):
            raise PaymentExceedsDebtError(Decimal("5"), Decimal("10"), "bob")
