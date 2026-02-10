from app.core.errors import DomainError

class NotMember(DomainError):
    def __init__(self):
        super().__init__(message="You are not a member of this chat. Use /join first.", code="not_member")

class UserNotRegistered(DomainError):
    def __init__(self):
        super().__init__(message="User not registered yet.", code="user_not_registered")

class ChatNotFound(DomainError):
    def __init__(self):
        super().__init__(message="Chat not found.", code="chat_not_found")

class ServerError(DomainError):
    def __init__(self):
        super().__init__(message="Error processing request. Please try again.", code="server_error")

class ExpenseNotFoundError(DomainError):
    def __init__(self, expense_id: int):
        super().__init__(message=f"Expense ({expense_id}) not found")

class ExpenseNotOwnedError(DomainError):
    def __init__(self, expense_id: int, username: str):
        super().__init__(message=f"Expense {expense_id} is not owned by {username}")
