class DomainError(Exception):
    """Base class for domain errors."""
    def __init__(self, message: str, code: str = "domain_error"):
        super().__init__(message)
        self.message = message
        self.code = code
