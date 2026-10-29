from typing import Any, Optional
from fastapi import HTTPException, status


class DomainException(Exception):
    """Base exception for all domain logic violations."""
    def __init__(self, message: str, code: str = "DOMAIN_ERROR", details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details


class InvalidStateTransitionError(DomainException):
    """Raised when an illegal state transition is attempted."""
    def __init__(self, current_state: str, attempted_state: str, entity_name: str, reason: str = ""):
        msg = f"Cannot transition {entity_name} from '{current_state}' to '{attempted_state}'. {reason}".strip()
        super().__init__(msg, code="INVALID_STATE_TRANSITION", details={
            "entity": entity_name,
            "current_state": current_state,
            "attempted_state": attempted_state,
            "reason": reason
        })


class SanitizationGateError(DomainException):
    """Raised when an item is attempted to be released for resale without passing data sanitization."""
    def __init__(self, item_id: str, reason: str):
        super().__init__(
            f"Sanitization gate violation for item {item_id}: {reason}",
            code="SANITIZATION_GATE_VIOLATION",
            details={"item_id": item_id, "reason": reason}
        )


class UnauthorizedActionError(DomainException):
    """Raised when an operation requiring approval has not been authorized."""
    def __init__(self, action: str, item_id: str, reason: str):
        super().__init__(
            f"Action '{action}' on item {item_id} is not authorized: {reason}",
            code="UNAUTHORIZED_RECOVERY_ACTION",
            details={"action": action, "item_id": item_id, "reason": reason}
        )


class ResourceNotFoundError(DomainException):
    """Raised when a requested resource does not exist."""
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            f"{resource_type} with ID '{resource_id}' was not found.",
            code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id}
        )
