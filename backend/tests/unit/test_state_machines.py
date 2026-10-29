import pytest
from backend.app.core.exceptions import InvalidStateTransitionError
from backend.app.domain.state_machines import StateMachineValidator
from backend.app.models.execution import SanitizationStatus
from backend.app.models.returns import ApprovalStatus, ReturnCaseStatus


def test_valid_return_case_transitions():
    # RETURN_REQUESTED -> PICKUP_ASSIGNED is valid
    StateMachineValidator.validate_return_case_transition(
        ReturnCaseStatus.RETURN_REQUESTED,
        ReturnCaseStatus.PICKUP_ASSIGNED,
        "item-123"
    )


def test_invalid_return_case_transition_raises_error():
    # RETURN_REQUESTED -> COMPLETED directly is illegal
    with pytest.raises(InvalidStateTransitionError) as exc:
        StateMachineValidator.validate_return_case_transition(
            ReturnCaseStatus.RETURN_REQUESTED,
            ReturnCaseStatus.COMPLETED,
            "item-123"
        )
    assert "Cannot transition" in str(exc.value)


def test_invalid_sanitization_transition():
    # NOT_STARTED -> PASSED directly without IN_PROGRESS raises error
    with pytest.raises(InvalidStateTransitionError):
        StateMachineValidator.validate_sanitization_transition(
            SanitizationStatus.NOT_STARTED,
            SanitizationStatus.PASSED,
            "item-123"
        )
