class ApplicationError(Exception):
    """Base error for expected application failures."""


class NotFoundError(ApplicationError):
    """Raised when a requested resource does not exist."""


class BusinessRuleError(ApplicationError):
    """Raised when a valid request breaks a business rule."""
