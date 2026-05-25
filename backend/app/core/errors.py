"""Custom exception classes for application-specific errors.

These exceptions are caught by FastAPI exception handlers and converted
to appropriate HTTP responses.
"""


class ApplicationError(Exception):
    """Base error for expected application failures."""


class NotFoundError(ApplicationError):
    """Raised when a requested resource does not exist (returns HTTP 404)."""


class BusinessRuleError(ApplicationError):
    """Raised when a valid request breaks a business rule (returns HTTP 409 Conflict).
    
    Examples: Cannot delete a car with an active rental, cannot change status
    without using proper rental flow.
    """
