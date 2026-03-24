from app.core.errors import DomainError
from decimal import Decimal


class NotMember(DomainError):
    def __init__(self, username: str = "You"):
        linking_verb = "are"
        if username != "You":
            linking_verb = "is"

        super().__init__(
            message=f"{username} {linking_verb} not a member of this chat. Use /join first.",
            code="not_member",
        )


class UserNotRegistered(DomainError):
    def __init__(self, message: str = "User is not registered yet."):
        super().__init__(message=f"{message}", code="user_not_registered")


class ChatNotFound(DomainError):
    def __init__(self):
        super().__init__(message="Chat not found.", code="chat_not_found")


class ServerError(DomainError):
    def __init__(self):
        super().__init__(
            message="Error processing request. Please try again.", code="server_error"
        )


class ExpenseNotFoundError(DomainError):
    def __init__(self, expense_id: int):
        super().__init__(
            message=f"Expense ({expense_id}) not found", code="expense_not_found"
        )


class ExpenseNotOwnedError(DomainError):
    def __init__(self, expense_id: int, username: str):
        super().__init__(
            message=f"Expense {expense_id} is not owned by {username}.",
            code="expense_not_owned",
        )


class NoDebtOwedError(DomainError):
    def __init__(self):
        super().__init__(message=f"You don't owe anyone money.", code="no_debt_owed")


class PaymentExceedsBalanceError(DomainError):
    def __init__(self, debt: Decimal, amount: Decimal):
        super().__init__(
            message=f"You only owe {debt} in total but tried to pay {amount}.",
            code="payment_exceeds_debt",
        )


class InvalidAmount(DomainError):
    def __init__(self):
        super().__init__(
            message="Amount must be greater than zero.",
            code="invalid_amount",
        )


class RecipientNotOwedError(DomainError):
    def __init__(self, to_username: str):
        super().__init__(
            message=f"@{to_username} is not owed anything in this chat.",
            code="recipient_not_owed",
        )
