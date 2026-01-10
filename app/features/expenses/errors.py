from app.core.errors import DomainError

class NotMember(DomainError):
    def __init__(self):
        super().__init__("You are not a member of this chat. Use /join first.", code="not_member")

class UserNotRegistered(DomainError):
    def __init__(self):
        super().__init__("User not registered yet.", code="user_not_registed")

class ChatNotFound(DomainError):
    def __init__(self):
        super().__init__("Chat not found.", code="chat_not_found")

class ServerError(DomainError):
    def __init__(self):
        super().__init__("Error processing request. Please try again.", code="server_error")
